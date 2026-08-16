# Plateforme d'investissement solidaire et participatif

Plateforme d'ESS (Économie Sociale et Solidaire) permettant à des petits
agriculteurs, éleveurs, artisans et commerçants marocains de solliciter
un financement participatif, remboursé **en nature** (huile d'argan,
safran, tapis, poterie, etc.). Deux IA sont intégrées :

- une **IA conversationnelle** qui guide et sensibilise à l'ESS,
- une **IA agentique** qui analyse chaque dossier soumis, calcule un score
  de pertinence et de risque de fraude, et suggère un verdict à un
  administrateur humain qui garde la décision finale.

## Structure

```
backend/          FastAPI + SQLAlchemy + Alembic + Celery
frontend/         React + Vite (SPA)
docker-compose.yml  Orchestration des 5 services
.env.example      Variables d'environnement à copier en .env
```

## Démarrage en une commande (Docker)

```bash
cp .env.example .env
# Renseigner au minimum GROQ_API_KEY et SECRET_KEY dans .env

docker compose up --build
```

Les services démarrent dans le bon ordre :
1. `postgres` et `redis`
2. `migrate` applique les migrations Alembic
3. `seed` peuple avec les données de démonstration
4. `api` (FastAPI, port 8000), `worker` (Celery), `frontend` (nginx, port 5173)

Une fois tout démarré :
- Frontend : http://localhost:5173
- API + Swagger : http://localhost:8000/docs

**Comptes de démonstration** (mot de passe : `demo1234`) :
- `admin@demo.ma` — file de validation avec rapports d'analyse IA
- `porteur@demo.ma` — 3 dossiers (brouillon, validé, en remboursement)
- `investisseur@demo.ma` — portefeuille avec suivi de livraisons

## Démarrage manuel (sans Docker)

Voir `backend/README.md` et `frontend/README.md`.

## Tests

```bash
# Backend (SQLite en mémoire, aucune dépendance externe requise)
cd backend
python e2e_test.py            # parcours métier complet
python refund_split_test.py   # répartition du remboursement entre plusieurs
                               # investisseurs situés dans des paliers différents
python agent_tools_test.py    # vérifications déterministes de l'agent d'analyse
                               # IA (budget, plan de remboursement, doublons,
                               # benchmark, documents, numéro légal), sans LLM
python golden_set_eval.py     # golden set : juge la qualité des verdicts IA sur
                               # des dossiers fictifs calibrés (VRAIS appels Groq,
                               # GROQ_API_KEY requis) — harnais anti-dérive à
                               # relancer après tout changement de prompt/modèle

# Backend sur un vrai PostgreSQL (recommandé avant mise en production)
TEST_DATABASE_URL=postgresql://user:pass@localhost/db python e2e_test.py

# Frontend (DOM simulé, aucun navigateur requis)
cd frontend
npm install
npm test
```

## Notes importantes de compatibilité

Plusieurs bugs de version ont été identifiés et corrigés au fil des tests
(voir `backend/README.md` pour le détail) : `passlib` cassé avec bcrypt 5.x,
`groq` 0.11.0 incompatible avec httpx récent, `email-validator` manquant du
requirements, `llama-3.3-70b-versatile` déprécié par Groq depuis juin 2026.
