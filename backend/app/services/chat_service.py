import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat import ChatConversation, ChatMessage
from app.models.enums import ChatRole, MessageSender
from app.services.groq_client import chat_completion_stream
from app.services.retrieval_service import format_context, retrieve

# Contexte commun — lève l'ambiguïté sur les acronymes du domaine
DOMAIN_CONTEXT = (
    "Contexte : sur cette plateforme, le sigle \"ESS\" désigne toujours "
    "l'Économie Sociale et Solidaire (jamais \"Employee Self Service\" ou "
    "un autre sens). Réponds sans hésitation avec cette définition si on te "
    "demande ce qu'est l'ESS."
)

# Style de réponse commun — appliqué à tous les rôles
STYLE_GUIDE = (
    "Style de réponse : réponds toujours de façon courte et engageante, "
    "va droit au but (quelques phrases ou une courte liste, pas de pavé de texte). "
    "Utilise un formatage markdown clair et aéré (titres courts, listes à puces, "
    "**gras** pour les points clés) et ajoute quelques emojis pertinents pour "
    "rendre la réponse chaleureuse et facile à lire. Si le sujet mérite plus de "
    "détails, termine par une question ou une proposition pour continuer la "
    "conversation plutôt que de tout expliquer d'un coup."
)

# Prompt système par rôle — c'est ici que se joue la "sensibilisation ESS"
SYSTEM_PROMPTS: dict[ChatRole, str] = {
    ChatRole.VISITEUR: (
        "Tu es l'assistant de la plateforme d'investissement solidaire et "
        "participatif. Explique le concept d'Économie Sociale et Solidaire "
        "(ESS) et le principe du remboursement en nature aux visiteurs, "
        "et guide-les vers l'inscription adaptée (porteur de projet ou investisseur). "
        f"{DOMAIN_CONTEXT} {STYLE_GUIDE}"
    ),
    ChatRole.PORTEUR: (
        "Tu assistes un porteur de projet (agriculteur, éleveur, artisan ou "
        "commerçant). Aide-le à construire un dossier clair et complet : description "
        "du projet, montant, plan de remboursement en nature réaliste. "
        "Ne donne jamais de conseil financier personnalisé, oriente vers l'équipe si besoin. "
        f"{DOMAIN_CONTEXT} {STYLE_GUIDE}"
    ),
    ChatRole.INVESTISSEUR: (
        "Tu assistes un investisseur solidaire. Explique les risques du "
        "financement participatif, le fonctionnement du remboursement en "
        "nature, et aide-le à comprendre les fiches projets. Ne fais jamais "
        "de recommandation d'investissement personnalisée. "
        f"{DOMAIN_CONTEXT} {STYLE_GUIDE}"
    ),
    ChatRole.ADMIN: f"Tu assistes un administrateur de la plateforme sur son usage. {DOMAIN_CONTEXT} {STYLE_GUIDE}",
}


def get_or_create_conversation(
    db: Session, user_id: uuid.UUID | None, context_role: ChatRole, project_id: uuid.UUID | None
) -> ChatConversation:
    conversation = ChatConversation(user_id=user_id, context_role=context_role, project_id=project_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def send_message_stream(db: Session, conversation_id: uuid.UUID, content: str, sender: MessageSender):
    """Générateur : yield les fragments de la réponse au fur et à mesure
    de leur génération par le LLM, puis persiste la réponse complète en
    DB une fois le flux terminé."""
    conversation = db.get(ChatConversation, conversation_id)

    db.add(ChatMessage(conversation_id=conversation_id, sender=sender, content=content))
    db.commit()

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPTS[conversation.context_role]}]

    if settings.RAG_ENABLED:
        chunks = retrieve(
            db,
            query=content,
            context_role=conversation.context_role,
            project_id=conversation.project_id,
            requesting_user_id=conversation.user_id,
        )
        context_block = format_context(chunks)
        if context_block:
            messages.append({
                "role": "system",
                "content": (
                    "Contexte pertinent trouvé dans la base de connaissances "
                    f"de la plateforme :\n\n{context_block}\n\n"
                    "Utilise ce contexte s'il répond à la question posée. "
                    "S'il ne contient pas la réponse, dis-le plutôt que "
                    "d'inventer une information."
                ),
            })

    messages += [
        {"role": "user" if m.sender == MessageSender.USER else "assistant", "content": m.content}
        for m in history
    ]

    full_reply = []
    for fragment in chat_completion_stream(messages, model=settings.GROQ_CHAT_MODEL):
        full_reply.append(fragment)
        yield fragment

    db.add(ChatMessage(
        conversation_id=conversation_id, sender=MessageSender.ASSISTANT, content="".join(full_reply),
    ))
    db.commit()
