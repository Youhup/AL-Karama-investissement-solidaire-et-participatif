"""Contenu pédagogique versionné, indexé pour le RAG du chat (FAQ ESS).

Remplace la logique auparavant codée en dur dans DOMAIN_CONTEXT côté
chat_service.py : ce contenu est maintenant récupéré par similarité
sémantique plutôt qu'injecté intégralement dans chaque prompt.

`context_role` restreint une entrée à un rôle (None = tous les rôles)."""

from app.models.enums import ChatRole

FAQ_ENTRIES = [
    {
        "id": "faq-ess-definition",
        "title": "Qu'est-ce que l'ESS ?",
        "content": (
            "Sur cette plateforme, le sigle \"ESS\" désigne toujours "
            "l'Économie Sociale et Solidaire (jamais \"Employee Self Service\" "
            "ou un autre sens). L'ESS regroupe des activités économiques à "
            "finalité sociale : elle privilégie l'utilité collective, "
            "l'entraide et le développement local plutôt que la seule "
            "recherche de profit."
        ),
        "context_role": None,
    },
    {
        "id": "faq-remboursement-nature",
        "title": "Comment fonctionne le remboursement en nature ?",
        "content": (
            "Sur cette plateforme, un porteur de projet financé ne rembourse "
            "pas ses investisseurs en argent, mais en nature : une partie de "
            "sa production (récoltes, produits artisanaux, services...) est "
            "livrée aux investisseurs selon un plan d'échéances défini au "
            "moment du financement. Chaque échéance a un statut (à venir, "
            "partiel, livré, en retard) suivi dans le tableau de bord de "
            "l'investisseur."
        ),
        "context_role": None,
    },
    {
        "id": "faq-porteur-deposer-dossier",
        "title": "Comment un porteur de projet dépose un dossier ?",
        "content": (
            "Un porteur de projet crée un dossier en brouillon avec un "
            "titre, une description claire du projet, le montant demandé et "
            "une durée de financement. Il peut y joindre des documents "
            "justificatifs (pièce d'identité, devis, registre de commerce...). "
            "Une fois complet, il soumet le dossier : il passe alors en "
            "analyse (une IA vérifie la cohérence du dossier), puis un "
            "administrateur valide ou rejette la demande. Un dossier soumis "
            "ne peut plus être modifié."
        ),
        "context_role": ChatRole.PORTEUR,
    },
    {
        "id": "faq-investisseur-risques",
        "title": "Quels sont les risques pour un investisseur solidaire ?",
        "content": (
            "Investir sur cette plateforme est un financement participatif "
            "solidaire : il n'y a pas de garantie de remboursement, et le "
            "retour se fait en nature, pas en argent. Le principal risque "
            "est que le porteur de projet ne puisse pas honorer tout ou "
            "partie de son plan de livraison (aléas de production, "
            "difficultés économiques...). Il est recommandé de diversifier "
            "ses investissements entre plusieurs projets plutôt que de tout "
            "miser sur un seul dossier."
        ),
        "context_role": ChatRole.INVESTISSEUR,
    },
    {
        "id": "faq-cycle-vie-dossier",
        "title": "Quelles sont les étapes de vie d'un dossier de projet ?",
        "content": (
            "Un dossier passe par les statuts suivants : brouillon (en "
            "cours de rédaction par le porteur), soumis, en analyse (IA), "
            "à valider (attente d'une décision humaine de l'administrateur), "
            "validé ou rejeté. Un dossier validé passe ensuite en "
            "financement le temps de récolter les investissements, puis "
            "financé une fois l'objectif atteint, puis en remboursement "
            "pendant les livraisons en nature, et enfin clos une fois "
            "toutes les échéances honorées."
        ),
        "context_role": None,
    },
]
