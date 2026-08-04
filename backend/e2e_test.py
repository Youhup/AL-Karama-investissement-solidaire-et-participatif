"""
Test d'intégration end-to-end du backend.
Mocks : Groq (chat + agent) et la tâche Celery (exécutée en synchrone).
Couvre le parcours métier complet de bout en bout.

Par défaut, tourne sur SQLite en mémoire (aucune dépendance externe).
Pour tester sur un vrai PostgreSQL (recommandé avant mise en production,
car JSONB et les ENUM natifs ne sont pas exercés par SQLite) :

    TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/ma_base \\
        python e2e_test.py
"""
import sys, os, uuid
sys.path.insert(0, '.')

TEST_DB_URL = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
IS_SQLITE = TEST_DB_URL.startswith('sqlite')

os.environ['DATABASE_URL'] = TEST_DB_URL
os.environ['GROQ_API_KEY'] = 'x'
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

print(f"Base de test : {'SQLite en mémoire' if IS_SQLITE else 'PostgreSQL réel'}")

if IS_SQLITE:
    # --- Patchs nécessaires uniquement pour SQLite ---
    # (JSONB et le cast automatique des UUID sont propres à Postgres)
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.types import JSON

    @compiles(JSONB, 'sqlite')
    def _compile_jsonb_sqlite(type_, compiler, **kw):
        return compiler.visit_JSON(JSON(), **kw)

    import uuid as _uuid
    from sqlalchemy.dialects.postgresql import UUID as _PGUUID

    _orig_bind = _PGUUID.bind_processor
    def _patched_bind(self, dialect):
        if dialect.name == 'sqlite':
            def process(value):
                if value is None:
                    return None
                return str(value if isinstance(value, _uuid.UUID) else _uuid.UUID(str(value)))
            return process
        return _orig_bind(self, dialect)
    _PGUUID.bind_processor = _patched_bind

    _orig_result = _PGUUID.result_processor
    def _patched_result(self, dialect, coltype):
        if dialect.name == 'sqlite':
            def process(value):
                return None if value is None else _uuid.UUID(str(value))
            return process
        return _orig_result(self, dialect, coltype)
    _PGUUID.result_processor = _patched_result

    # DateTime(timezone=True) : sur PostgreSQL, une lecture renvoie toujours
    # un datetime *aware*. SQLite n'a aucune notion de fuseau horaire ; pour
    # ce dialecte, SQLAlchemy route le type générique DateTime vers sa propre
    # implémentation (sqlalchemy.dialects.sqlite.base.DATETIME, cf. colspecs)
    # qui renvoie des datetimes *naive*, ce qui casse toute comparaison avec
    # `datetime.now(timezone.utc)` (ex. project_service.expire_funding_if_overdue).
    # On force l'UTC au retour, uniquement sur cette classe spécifique au
    # dialecte SQLite.
    from datetime import timezone as _timezone
    from sqlalchemy.dialects.sqlite.base import DATETIME as _SQLiteDATETIME

    _orig_dt_result = _SQLiteDATETIME.result_processor
    def _patched_dt_result(self, dialect, coltype):
        orig = _orig_dt_result(self, dialect, coltype)
        def process(value):
            value = orig(value) if orig else value
            if value is not None and value.tzinfo is None:
                value = value.replace(tzinfo=_timezone.utc)
            return value
        return process
    _SQLiteDATETIME.result_processor = _patched_dt_result

# --- Mock du client Groq AVANT import des services ---
import app.services.chat_service as chat_service
import app.services.agentic_analysis.agent as agent_module

class FakeMsg:
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []

chat_service.chat_completion_stream = lambda messages, model: iter(
    ["Réponse simulée ", "de l'assistant ESS."]
)
if IS_SQLITE:
    # retrieval_service.retrieve() trie par similarité vectorielle via
    # l'opérateur pgvector `<=>` (KnowledgeChunk.embedding.cosine_distance),
    # propre à l'extension PostgreSQL pgvector : inexploitable sur SQLite.
    # Le RAG n'étant pas ce que ce test vérifie (juste que /chat fonctionne
    # de bout en bout), on le neutralise ici plutôt que d'inventer un
    # substitut. Sur un vrai PostgreSQL (TEST_DATABASE_URL), la vraie
    # recherche vectorielle s'exécute normalement.
    chat_service.retrieve = lambda *a, **kw: []
# L'agent renvoie directement un verdict JSON (pas de tool call) pour le test
agent_module.chat_completion = lambda messages, model, tools=None: FakeMsg(
    '{"relevance_score": 80, "fraud_risk_score": 15, "verdict": "recommande", '
    '"findings": [{"type": "ok", "severite": "faible", "description": "RAS"}]}'
)

# --- Exécuter la tâche Celery en synchrone (pas de worker/redis) ---
from app.services.agentic_analysis.agent import trigger_project_analysis
trigger_project_analysis.delay = lambda project_id: trigger_project_analysis(project_id)

# --- DB de test partagée ---
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.session import Base, get_db
import app.db.session as db_session

# Importer TOUS les modèles avant create_all pour que les FK résolvent
# leurs tables cibles (sinon projects.sector_id -> sectors échoue).
import app.models.user, app.models.sector, app.models.project
import app.models.document, app.models.investment, app.models.refund
import app.models.ai_report, app.models.chat  # noqa: F401

if IS_SQLITE:
    engine = create_engine(TEST_DB_URL, connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
else:
    from sqlalchemy import text
    engine = create_engine(TEST_DB_URL)
    # Repart d'un schéma totalement propre. On recrée le schéma public
    # plutôt que d'utiliser drop_all : celui-ci ignore toute table créée
    # par une migration Alembic mais sans modèle SQLAlchemy correspondant,
    # et échoue sur leurs contraintes FK.
    with engine.connect() as conn:
        conn.execute(text('DROP SCHEMA public CASCADE'))
        conn.execute(text('CREATE SCHEMA public'))
        # DROP SCHEMA supprime aussi l'extension pgvector (créée par la
        # migration Alembic d815eb945778) : sans elle, knowledge_chunks.embedding
        # (type VECTOR) ne peut pas être créée par create_all ci-dessous.
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
        conn.commit()
    Base.metadata.create_all(engine)

TestSession = sessionmaker(bind=engine)
# La tâche agent utilise SessionLocal directement -> on le pointe vers la DB de test
db_session.SessionLocal = TestSession
agent_module.SessionLocal = TestSession

def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

from app.main import app
from fastapi.testclient import TestClient
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# Seed secteurs
from app.models.sector import Sector
_s = TestSession()
_s.add_all([Sector(id=1, name='Agriculture'), Sector(id=2, name='Artisanat')])
_s.commit()
_s.close()

failures = []
def check(label, condition):
    status = 'OK ' if condition else 'FAIL'
    if not condition: failures.append(label)
    print(f'  [{status}] {label}')

print('\n=== 1. Inscription des 3 rôles ===')
r = client.post('/auth/register', json={'email': 'porteur@t.com', 'password': 'password123', 'full_name': 'Ahmed Porteur', 'role': 'porteur'})
check('register porteur -> 201', r.status_code == 201)
r = client.post('/auth/register', json={'email': 'inv@t.com', 'password': 'password123', 'full_name': 'Sara Inv', 'role': 'investisseur'})
check('register investisseur -> 201', r.status_code == 201)
# Personne ne doit pouvoir s'auto-inscrire admin (cf. app/schemas/user.py :
# UserCreate.role est un Literal restreint à porteur/investisseur).
r = client.post('/auth/register', json={'email': 'wannabe-admin@t.com', 'password': 'password123', 'full_name': 'X', 'role': 'admin'})
check('auto-inscription admin refusée -> 422', r.status_code == 422)
# admin : créé en base directement (pas d'auto-inscription admin en prod)
from app.models.user import User
from app.core.security import hash_password
from app.models.enums import UserRole
_s = TestSession()
admin = User(id=uuid.uuid4(), email='admin@t.com', password_hash=hash_password('password123'), full_name='Admin', role=UserRole.ADMIN)
_s.add(admin); _s.commit(); _s.close()

print('\n=== 2. Connexion (form-urlencoded) ===')
r = client.post('/auth/login', data={'username': 'porteur@t.com', 'password': 'password123'})
check('login porteur -> 200', r.status_code == 200)
porteur_tok = r.json()['access_token']
r = client.post('/auth/login', data={'username': 'inv@t.com', 'password': 'password123'})
inv_tok = r.json()['access_token']
r = client.post('/auth/login', data={'username': 'admin@t.com', 'password': 'password123'})
admin_tok = r.json()['access_token']
r = client.post('/auth/login', data={'username': 'porteur@t.com', 'password': 'MAUVAIS'})
check('login mauvais mdp -> 401', r.status_code == 401)

H = lambda t: {'Authorization': f'Bearer {t}'}

print('\n=== 3. Création + plan de remboursement + soumission projet (déclenche analyse IA) ===')
r = client.post('/projects', headers=H(porteur_tok), json={'title': 'Coop Argane', 'description': "Extraction d'huile d'argan par 12 femmes.", 'sector_id': 1, 'amount_requested': 20000, 'funding_duration_days': 60, 'city': 'Essaouira'})
check('create projet -> 201', r.status_code == 201)
pid = r.json()['id']
check('statut initial brouillon', r.json()['status'] == 'brouillon')
# un investisseur ne doit pas pouvoir créer de projet
r = client.post('/projects', headers=H(inv_tok), json={'title': 'x', 'description': 'y', 'sector_id': 1, 'amount_requested': 1000})
check('investisseur ne peut pas créer projet -> 403', r.status_code == 403)

# Le plan de remboursement (paliers) se définit pendant que le dossier est
# encore en brouillon : submit_project exige qu'il existe déjà (cf.
# refunds.py / PLAN_CREATABLE_STATUSES).
r = client.post(f'/projects/{pid}/refund-plan', headers=H(porteur_tok), json={
    'start_date': '2026-08-01',
    'tiers': [{
        'tier_min_amount': 100,
        'product_description': "Huile d'argan",
        'unit': 'litre',
        'quantity_per_occurrence': 30,
        'frequency': 'mensuelle',
        'installments_count': 4,
    }],
})
check('création plan remboursement -> 201', r.status_code == 201)
plan = r.json()
check('4 échéances générées à la création du plan', len(plan['installments']) == 4)
check('quantités = 30 par échéance', all(float(i['quantity_due']) == 30 for i in plan['installments']))
check('aucune allocation avant tout investissement', all(len(i['allocations']) == 0 for i in plan['installments']))

r = client.post(f'/projects/{pid}/submit', headers=H(porteur_tok))
check('submit projet -> 200', r.status_code == 200)
# après analyse synchrone, le projet doit être passé en a_valider
r = client.get(f'/projects/{pid}')
check('statut après analyse = a_valider', r.json()['status'] == 'a_valider')

print('\n=== 4. Revue admin ===')
r = client.get('/admin/projects', headers=H(admin_tok))
check('admin liste projets -> 200', r.status_code == 200)
r = client.get(f'/admin/projects/{pid}/analysis', headers=H(admin_tok))
check('admin voit rapport IA -> 200', r.status_code == 200)
check('verdict IA = recommande', r.json().get('verdict') == 'recommande')
check('score pertinence = 80', r.json().get('relevance_score') == 80)
# un porteur ne doit pas accéder à l'espace admin
r = client.get('/admin/projects', headers=H(porteur_tok))
check('porteur bloqué sur /admin -> 403', r.status_code == 403)

r = client.post(f'/admin/projects/{pid}/decision', headers=H(admin_tok), json={'decision': 'valide', 'notes': 'OK'})
check('admin valide projet -> 200', r.status_code == 200)
r = client.get(f'/projects/{pid}')
check('projet passé en valide', r.json()['status'] == 'valide')

print('\n=== 5. Investissement (avec verrouillage) ===')
# projet visible dans la liste publique désormais
r = client.get('/projects')
check('projet validé visible publiquement', any(p['id'] == pid for p in r.json()))
r = client.post(f'/projects/{pid}/investments', headers=H(inv_tok), json={'amount': 20000})
check('investissement total -> 201', r.status_code == 201)
r = client.get(f'/projects/{pid}')
# Le plan de remboursement existait déjà avant la fin du financement (étape 3) :
# le projet saute directement à en_remboursement plutôt que de s'arrêter à
# finance (cf. create_investment dans investments.py).
check('projet passé en en_remboursement (objectif atteint, plan déjà défini)', r.json()['status'] == 'en_remboursement')
check('amount_raised = 20000', float(r.json()['amount_raised']) == 20000)
# on ne peut plus investir sur un projet financé
r = client.post(f'/projects/{pid}/investments', headers=H(inv_tok), json={'amount': 100})
check('investir sur projet financé -> 400', r.status_code == 400)
# le porteur ne peut pas investir
r2 = client.post('/projects', headers=H(porteur_tok), json={'title': 'P2', 'description': 'desc2', 'sector_id': 1, 'amount_requested': 5000})
pid2 = r2.json()['id']
r = client.post(f'/projects/{pid2}/investments', headers=H(porteur_tok), json={'amount': 100})
check('porteur ne peut pas investir (rôle) -> 403', r.status_code == 403)

print('\n=== 6. Remboursement en nature ===')
# Le plan existait déjà avant la fin du financement (étape 3) : le projet
# bascule directement en en_remboursement une fois entièrement financé.
r = client.get(f'/projects/{pid}')
check('projet passé en en_remboursement', r.json()['status'] == 'en_remboursement')
r = client.get(f'/projects/{pid}/refund-plan', headers=H(porteur_tok))
check('lecture plan -> 200', r.status_code == 200)
plan = r.json()
check('4 échéances toujours présentes', len(plan['installments']) == 4)
check('chaque échéance a 1 allocation (1 investisseur)', all(len(i['allocations']) == 1 for i in plan['installments']))
# livrer la 1ère échéance
first_inst = plan['installments'][0]['id']
r = client.post(f'/refund-installments/{first_inst}/deliver', headers=H(porteur_tok))
check('livraison échéance 1 -> 200', r.status_code == 200)
check('échéance 1 marquée livre', r.json()['status'] == 'livre')

print('\n=== 7. Suivi côté investisseur ===')
r = client.get('/investments/me', headers=H(inv_tok))
check('investisseur voit ses investissements', r.status_code == 200 and len(r.json()) == 1)
inv_id = r.json()[0]['id']
r = client.get(f'/investments/{inv_id}/refund-allocations', headers=H(inv_tok))
check('suivi remboursement -> 200', r.status_code == 200)
check('4 allocations retournées', len(r.json()) == 4)
check('allocation 1 a date + numéro échéance', r.json()[0].get('due_date') is not None and r.json()[0].get('installment_number') == 1)

print('\n=== 8. Chat IA (visiteur anonyme) ===')
r = client.post('/chat/conversations')
check('conversation anonyme -> 200', r.status_code == 200)
cid = r.json()['conversation_id']
r = client.post(f'/chat/conversations/{cid}/messages', json={'content': "C'est quoi l'ESS ?"})
check('message chat -> 200 (stream)', r.status_code == 200 and "Réponse simulée" in r.text)

print('\n' + '='*40)
if failures:
    print(f'ÉCHECS ({len(failures)}):')
    for f in failures: print('  -', f)
    print('RESULT: FAIL')
    sys.exit(1)
else:
    print('RESULT: ALL PASS')
