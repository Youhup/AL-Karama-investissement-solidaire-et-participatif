import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_optional_user
from app.models.chat import ChatConversation
from app.models.enums import ChatRole, MessageSender
from app.models.user import User
from app.schemas.chat import ChatMessageIn
from app.services.chat_service import get_or_create_conversation, send_message_stream

router = APIRouter(prefix="/chat", tags=["Chat IA"])


@router.post("/conversations")
def start_conversation(
    context_role: ChatRole = ChatRole.VISITEUR,
    project_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Ouvert aux visiteurs anonymes (get_optional_user ne lève jamais de
    401) — c'est tout le sens de ChatRole.VISITEUR par défaut : quelqu'un
    qui n'est pas encore inscrit doit pouvoir poser des questions.

    Le rôle de contexte est TOUJOURS dérivé du token, jamais du paramètre
    client : context_role conditionne l'accès RAG aux dossiers non publics
    (cf. retrieval_service._can_access_project_chunks, qui donne un accès
    étendu au rôle admin). Sans cela, un visiteur anonyme pourrait ouvrir
    une conversation avec ?context_role=admin et lire le contenu indexé
    d'un brouillon ou la note de décision d'un dossier rejeté. Le paramètre
    est conservé pour compatibilité mais ignoré dès qu'il réclame plus que
    ce que le token prouve."""
    effective_role = ChatRole(current_user.role.value) if current_user else ChatRole.VISITEUR
    conversation = get_or_create_conversation(
        db, user_id=current_user.id if current_user else None,
        context_role=effective_role, project_id=project_id,
    )
    return {"conversation_id": conversation.id}


@router.post("/conversations/{conversation_id}/messages")
def post_message(conversation_id: uuid.UUID, payload: ChatMessageIn, db: Session = Depends(get_db)):
    """Envoie un message utilisateur et stream la réponse de l'IA conversationnelle
    au fil de sa génération (texte brut, chunké) plutôt que d'attendre la
    réponse complète — l'utilisateur voit les premiers mots apparaître
    pendant que le reste se génère encore.

    L'IA reste PUREMENT informative ici : guidage sur le site, sensibilisation
    à l'ESS, explication du mécanisme de remboursement en nature. Elle ne
    modifie jamais un dossier ou un investissement (pas de tool calling ici,
    contrairement à l'agent d'analyse)."""
    if db.get(ChatConversation, conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return StreamingResponse(
        send_message_stream(db, conversation_id=conversation_id, content=payload.content, sender=MessageSender.USER),
        media_type="text/plain; charset=utf-8",
    )
