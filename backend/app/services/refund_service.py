from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.models.enums import InvestmentStatus, RepaymentFrequency
from app.models.investment import Investment
from app.models.refund import InvestmentRefundAllocation, RefundInstallment, RefundPlan, RefundTier

# Montant minimum d'investissement autorisé sur la plateforme : fixe le
# plancher du premier palier de tout plan de remboursement.
PLATFORM_MIN_INVESTMENT = 100

# Pas entre deux échéances consécutives, par fréquence. "à la récolte" est
# une approximation (cycle semestriel) : le porteur ajuste les dates réelles
# à la livraison, ce champ ne fixe qu'un calendrier indicatif de départ.
_FREQUENCY_STEP = {
    RepaymentFrequency.HEBDOMADAIRE: lambda i: timedelta(weeks=i),
    RepaymentFrequency.MENSUELLE: lambda i: relativedelta(months=i),
    RepaymentFrequency.TRIMESTRIELLE: lambda i: relativedelta(months=3 * i),
    RepaymentFrequency.UNIQUE: lambda i: relativedelta(months=0),
    RepaymentFrequency.A_LA_RECOLTE: lambda i: relativedelta(months=6 * i),
}


def validate_tier_chain(tiers: list[RefundTier]) -> None:
    """Vérifie que les paliers sont contigus, démarrent au minimum de la
    plateforme, et que seul le dernier reste ouvert (pas de plafond)."""
    if not tiers:
        raise ValueError("Au moins un palier est requis")

    ordered = sorted(tiers, key=lambda t: float(t.tier_min_amount))

    if float(ordered[0].tier_min_amount) != PLATFORM_MIN_INVESTMENT:
        raise ValueError(
            f"Le premier palier doit démarrer à {PLATFORM_MIN_INVESTMENT} MAD "
            "(montant minimum d'investissement de la plateforme)"
        )

    for i, tier in enumerate(ordered):
        tier_max = tier.tier_max_amount
        if tier_max is not None and float(tier_max) < float(tier.tier_min_amount):
            raise ValueError(f"Le palier {i + 1} a un maximum inférieur à son minimum")

        is_last = i == len(ordered) - 1
        if is_last:
            if tier_max is not None:
                raise ValueError("Le dernier palier doit rester ouvert (pas de montant maximum)")
            continue

        if tier_max is None:
            raise ValueError(f"Le palier {i + 1} doit avoir un montant maximum (seul le dernier peut être ouvert)")

        next_tier = ordered[i + 1]
        if float(next_tier.tier_min_amount) != float(tier_max) + 1:
            raise ValueError(
                f"Le palier {i + 2} doit démarrer à {float(tier_max) + 1} MAD "
                f"(lendemain du maximum du palier {i + 1})"
            )


def estimate_tier_coverage(tier: RefundTier) -> tuple[float, bool] | tuple[None, None]:
    """Valeur totale estimée du palier sur toute sa durée, et si elle couvre
    le montant minimum investi de la tranche. (None, None) si le porteur n'a
    renseigné aucune valeur unitaire estimée — l'estimation est facultative."""
    if tier.estimated_unit_value is None:
        return None, None
    total_value = (
        float(tier.quantity_per_occurrence) * float(tier.estimated_unit_value) * tier.installments_count
    )
    return total_value, total_value >= float(tier.tier_min_amount)


def generate_installments(db: Session, tier: RefundTier, start_date: date) -> list[RefundInstallment]:
    count = 1 if tier.frequency == RepaymentFrequency.UNIQUE else tier.installments_count
    step = _FREQUENCY_STEP[tier.frequency]

    installments = []
    for i in range(count):
        installment = RefundInstallment(
            refund_tier_id=tier.id,
            installment_number=i + 1,
            due_date=start_date + step(i),
            quantity_due=tier.quantity_per_occurrence,
        )
        db.add(installment)
        installments.append(installment)

    db.flush()
    return installments


def generate_allocations(
    db: Session, project_id, tier: RefundTier, installments: list[RefundInstallment]
) -> None:
    """Chaque investisseur dont le montant investi tombe dans ce palier reçoit
    la même quantité fixe par échéance — contrairement à l'ancien modèle, ce
    n'est plus une répartition proportionnelle : le palier définit une
    contrepartie forfaitaire, pas une part d'un total à diviser."""
    investments = (
        db.query(Investment)
        .filter(Investment.project_id == project_id, Investment.status == InvestmentStatus.CONFIRME)
        .all()
    )
    tier_min = float(tier.tier_min_amount)
    tier_max = float(tier.tier_max_amount) if tier.tier_max_amount is not None else None
    tier_investments = [
        inv
        for inv in investments
        if float(inv.amount) >= tier_min and (tier_max is None or float(inv.amount) <= tier_max)
    ]

    for installment in installments:
        for investment in tier_investments:
            db.add(
                InvestmentRefundAllocation(
                    installment_id=installment.id,
                    investment_id=investment.id,
                    quantity_allocated=tier.quantity_per_occurrence,
                )
            )


def generate_allocations_for_investment(db: Session, investment: Investment) -> None:
    """Alloue les échéances d'un plan de remboursement déjà existant à un
    investisseur qui rejoint le projet après coup (le plan peut désormais être
    défini avant la fin du financement, cf. create_refund_plan)."""
    plan = db.query(RefundPlan).filter(RefundPlan.project_id == investment.project_id).first()
    if not plan:
        return

    tiers = db.query(RefundTier).filter(RefundTier.refund_plan_id == plan.id).all()
    amount = float(investment.amount)
    tier = next(
        (
            t
            for t in tiers
            if amount >= float(t.tier_min_amount)
            and (t.tier_max_amount is None or amount <= float(t.tier_max_amount))
        ),
        None,
    )
    if not tier:
        return

    installments = (
        db.query(RefundInstallment).filter(RefundInstallment.refund_tier_id == tier.id).all()
    )
    for installment in installments:
        db.add(
            InvestmentRefundAllocation(
                installment_id=installment.id,
                investment_id=investment.id,
                quantity_allocated=tier.quantity_per_occurrence,
            )
        )
