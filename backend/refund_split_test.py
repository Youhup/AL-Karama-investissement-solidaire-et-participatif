"""Test ciblé : répartition du remboursement en nature entre PLUSIEURS
investisseurs situés dans des paliers (tiers) différents ou identiques.

Le modèle n'est plus une répartition proportionnelle à la part investie
(cf. app/services/refund_service.py::generate_allocations) : chaque palier
définit une contrepartie forfaitaire fixe, versée intégralement à tout
investisseur dont le montant tombe dans sa plage — deux investisseurs du
même palier reçoivent donc exactement la même quantité, même si leurs
montants investis diffèrent. C'est précisément ce que ce test vérifie."""
import sys, os, uuid
sys.path.insert(0, '.')
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['GROQ_API_KEY'] = 'x'; os.environ['SECRET_KEY'] = 's'; os.environ['REDIS_URL'] = 'redis://x'

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID as _PGUUID
from sqlalchemy.types import JSON
import uuid as _uuid

@compiles(JSONB, 'sqlite')
def _c(t, comp, **kw): return comp.visit_JSON(JSON(), **kw)

_ob = _PGUUID.bind_processor
def _pb(self, d):
    if d.name == 'sqlite':
        return lambda v: None if v is None else str(v if isinstance(v, _uuid.UUID) else _uuid.UUID(str(v)))
    return _ob(self, d)
_PGUUID.bind_processor = _pb
_or = _PGUUID.result_processor
def _pr(self, d, ct):
    if d.name == 'sqlite':
        return lambda v: None if v is None else _uuid.UUID(str(v))
    return _or(self, d, ct)
_PGUUID.result_processor = _pr

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.session import Base
import app.models.user, app.models.sector, app.models.project
import app.models.document, app.models.investment, app.models.refund, app.models.ai_report, app.models.chat

from app.models.investment import Investment
from app.models.refund import RefundPlan, RefundTier, InvestmentRefundAllocation
from app.models.enums import InvestmentStatus, RepaymentFrequency
from app.services.refund_service import generate_installments, generate_allocations, validate_tier_chain
import datetime

engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False}, poolclass=StaticPool)
TS = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

db = TS()
pid = _uuid.uuid4()

# 3 investisseurs : 2000 MAD (palier "petit"), 3000 et 5000 MAD (palier
# "grand") — montants volontairement différents à l'intérieur du même
# palier pour vérifier qu'ils reçoivent bien la MÊME quantité forfaitaire.
investments = {}
for amt in (2000, 3000, 5000):
    inv = Investment(id=_uuid.uuid4(), project_id=pid, investor_id=_uuid.uuid4(),
                      amount=amt, status=InvestmentStatus.CONFIRME,
                      invested_at=datetime.datetime.now())
    db.add(inv)
    investments[amt] = inv
db.commit()

plan = RefundPlan(id=_uuid.uuid4(), project_id=pid, start_date=datetime.date(2026, 8, 1))
db.add(plan); db.flush()

# Palier 1 : 100 à 2999 MAD -> 5 litres/échéance. Palier 2 (ouvert) : à
# partir de 3000 MAD -> 15 litres/échéance. Chaîne contiguë, cf.
# validate_tier_chain (démarre à PLATFORM_MIN_INVESTMENT=100).
tier_small = RefundTier(id=_uuid.uuid4(), refund_plan_id=plan.id, tier_min_amount=100,
                        tier_max_amount=2999, product_description='Huile (petit palier)',
                        unit='litre', quantity_per_occurrence=5,
                        frequency=RepaymentFrequency.MENSUELLE, installments_count=3)
tier_big = RefundTier(id=_uuid.uuid4(), refund_plan_id=plan.id, tier_min_amount=3000,
                      tier_max_amount=None, product_description='Huile (grand palier)',
                      unit='litre', quantity_per_occurrence=15,
                      frequency=RepaymentFrequency.MENSUELLE, installments_count=3)

failures = []
def check(label, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    if not cond: failures.append(label)

try:
    validate_tier_chain([tier_small, tier_big])
    check('chaîne de paliers valide (contiguë, démarre à 100, dernier ouvert)', True)
except ValueError as exc:
    check(f'chaîne de paliers valide ({exc})', False)

for tier in (tier_small, tier_big):
    db.add(tier)
    db.flush()
    installments = generate_installments(db, tier, plan.start_date)
    generate_allocations(db, pid, tier, installments)
db.commit()

# Ré-interroge en base plutôt que de garder les objets Python en mémoire.
from app.models.refund import RefundInstallment
insts_small = db.query(RefundInstallment).filter(RefundInstallment.refund_tier_id == tier_small.id).all()
insts_big = db.query(RefundInstallment).filter(RefundInstallment.refund_tier_id == tier_big.id).all()

check('palier petit : 3 échéances générées', len(insts_small) == 3)
check('palier petit : quantité due = 5 litres/échéance', all(float(i.quantity_due) == 5 for i in insts_small))
check('palier grand : 3 échéances générées', len(insts_big) == 3)
check('palier grand : quantité due = 15 litres/échéance', all(float(i.quantity_due) == 15 for i in insts_big))

for inst in insts_small:
    allocs = db.query(InvestmentRefundAllocation).filter(InvestmentRefundAllocation.installment_id == inst.id).all()
    check(f'palier petit #{inst.installment_number}: 1 allocation (1 investisseur dans ce palier)', len(allocs) == 1)
    check(f'palier petit #{inst.installment_number}: quantité allouée = 5', allocs and float(allocs[0].quantity_allocated) == 5)
    check(f'palier petit #{inst.installment_number}: alloué au bon investisseur (2000 MAD)',
          allocs and allocs[0].investment_id == investments[2000].id)

for inst in insts_big:
    allocs = db.query(InvestmentRefundAllocation).filter(InvestmentRefundAllocation.installment_id == inst.id).all()
    check(f'palier grand #{inst.installment_number}: 2 allocations (2 investisseurs dans ce palier)', len(allocs) == 2)
    quantities = {float(a.quantity_allocated) for a in allocs}
    check(f'palier grand #{inst.installment_number}: 3000 MAD et 5000 MAD reçoivent la MÊME quantité (15), pas une part proportionnelle',
          quantities == {15})

print()
if failures:
    print(f'ÉCHECS ({len(failures)}):')
    for f in failures: print('  -', f)
    print('RESULT: FAIL'); sys.exit(1)
else:
    print('RESULT: ALL PASS')
