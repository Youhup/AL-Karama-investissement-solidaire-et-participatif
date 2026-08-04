# Backend — Plateforme d'investissement solidaire

## Structure

```
app/
  core/          # config, sécurité (JWT, hash)
  db/            # session SQLAlchemy, Base déclarative
  models/        # tables SQLAlchemy
  schemas/       # schémas Pydantic (validation/serialisation API)
  routers/       # endpoints FastAPI, groupés par domaine
  services/
    groq_client.py           # wrapper unique autour de l'API Groq
    chat_service.py          # IA conversationnelle (guidage, sensibilisation ESS)
    agentic_analysis/        # IA agentique (analyse de dossier, tool calling)
  dependencies.py            # auth courante, contrôle de rôle (RBAC)
  main.py                    # assemble l'app FastAPI
```

## Lancer en local

```bash
# Dépendances système requises pour l'OCR (Ubuntu/Debian) :
# sudo apt install tesseract-ocr tesseract-ocr-fra tesseract-ocr-ara poppler-utils

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # renseigner DATABASE_URL, GROQ_API_KEY, SECRET_KEY

alembic upgrade head   # crée les tables

uvicorn app.main:app --reload

# Dans un autre terminal : le worker Celery (OCR + analyse agentique)
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

## Migrations (Alembic)

```bash
alembic upgrade head              # applique toutes les migrations
alembic revision --autogenerate -m "description"  # nouvelle migration
alembic downgrade -1              # revient d'une migration en arrière
```

## Données de démonstration

```bash
python seed_demo.py            # peuple la base
python seed_demo.py --reset    # vide les tables métier avant de peupler
```

Crée 5 comptes (mot de passe : `demo1234`) et 5 projets à différents stades
du cycle de vie, avec plan de remboursement en cours pour l'un d'eux.

## Compte administrateur (production)

`POST /auth/register` n'accepte volontairement que les rôles `porteur` et
`investisseur` (cf. `app/schemas/user.py`) : aucune auto-inscription admin
n'est possible via l'API, en prod comme ailleurs. Le premier compte admin
(ou sa récupération en cas de mot de passe perdu) se crée hors ligne :

```bash
python create_admin.py --email admin@exemple.ma --name "Administrateur"
# mot de passe demandé de façon interactive (jamais en argument CLI)
```

Si l'email existe déjà, le script demande confirmation puis promeut le
compte admin et réinitialise son mot de passe.

## Tests

Deux scripts de test d'intégration sont fournis à la racine du backend
(ils tournent sur une base SQLite en mémoire, avec Groq et Celery mockés —
aucune dépendance externe requise ; l'upload de documents/OCR n'est pas
exercé par ces scripts) :

```bash
python e2e_test.py           # parcours complet : inscription -> dépôt ->
                             # plan de remboursement -> soumission ->
                             # analyse IA -> validation admin -> investissement
                             # -> remboursement en nature -> suivi -> chat
python refund_split_test.py  # répartition du remboursement entre plusieurs
                             # investisseurs situés dans des paliers différents
```

## Notes de compatibilité (importantes)

Plusieurs versions ont été ajustées après tests d'intégration réels :

- **`passlib` retiré au profit de `bcrypt` directement** : passlib 1.7.4
  (non maintenu depuis 2020) est cassé avec bcrypt >= 4.1 et fait planter
  toute inscription/connexion. `app/core/security.py` utilise désormais
  `bcrypt` directement.
- **`groq` monté de 0.11.0 à 0.30.0** : la 0.11.0 passe un argument
  `proxies` supprimé dans les httpx récents, ce qui empêche le client
  Groq de s'instancier (chat + agent inutilisables).
- **`email-validator` ajouté** : requis par `pydantic.EmailStr` mais
  absent du requirements initial (l'app plantait au démarrage).
- **Modèle Groq par défaut** : `llama-3.3-70b-versatile` a été déprécié
  par Groq (annonce du 17/06/2026) ; la config pointe désormais vers
  `openai/gpt-oss-120b`. Vérifier https://console.groq.com/docs/models
  avant la mise en production.

## Ce qui est complet dans ce squelette

- Auth (register/login/JWT) — `routers/auth.py`
- Cycle de vie complet d'un projet, y compris la soumission qui déclenche
  l'analyse IA en tâche de fond — `routers/projects.py`
- IA conversationnelle avec prompt adapté au rôle (visiteur/porteur/investisseur)
  — `services/chat_service.py`
- IA agentique avec boucle de tool calling (Groq function calling) et
  sauvegarde du rapport en base — `services/agentic_analysis/agent.py`
- Validation humaine obligatoire après le rapport IA — `routers/admin.py`
- Upload de documents + OCR asynchrone (image directe, PDF natif ou
  scanné avec fallback OCR) — `routers/documents.py`, `services/ocr_service.py`
- Investissements avec verrouillage transactionnel (`SELECT FOR UPDATE`)
  pour éviter tout dépassement du montant demandé en cas de requêtes
  concurrentes, et transition automatique de statut du projet
  (`valide → en_financement → finance`) — `routers/investments.py`
- Remboursement en nature : plan global → échéances datées (mensuel/
  trimestriel) → répartition proportionnelle entre investisseurs figée
  à la création du plan, avec ajustement d'arrondi pour que la somme
  des parts corresponde exactement à la quantité due, et clôture
  automatique du projet (`clos`) une fois toutes les échéances livrées
  — `routers/refunds.py`, `services/refund_service.py`

## Idées d'amélioration (hors MVP)

- Intégration d'un vrai fournisseur de paiement (CMI, Stripe) pour les
  investissements, au lieu de la confirmation immédiate actuelle
- Notifications (email/push) à chaque changement de statut de dossier,
  chaque échéance de remboursement approchant, etc. — table `notifications`
  déjà présente en base (`models/notification.py`), il ne manque que le
  service d'envoi
- Relations ORM explicites (`relationship()`) entre les modèles si le
  chargement manuel dans `refunds.py` devient trop verbeux
