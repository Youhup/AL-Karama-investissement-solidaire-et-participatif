"""
Peuple la base avec un jeu de données de démonstration cohérent :
comptes des trois rôles, projets à différents stades du cycle de vie,
investissements, plan de remboursement en nature et rapports d'analyse IA.

Usage (depuis backend/, la base doit déjà exister et être migrée) :

    python seed_demo.py            # peuple
    python seed_demo.py --reset    # vide les tables métier puis peuple

Comptes créés (mot de passe identique pour tous : « demo1234 ») :
    porteur@demo.ma        (porteur de projet)
    porteur2@demo.ma       (porteur de projet)
    investisseur@demo.ma   (investisseur)
    investisseur2@demo.ma  (investisseur)
    admin@demo.ma          (administrateur)
"""
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, ".")

from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (  # noqa: F401  (import central : enregistre toutes les tables)
    AIAnalysisReport,
    Document,
    Investment,
    Project,
    Sector,
    User,
)
from app.models.enums import (
    AnalysisVerdict,
    InvestmentStatus,
    ProjectStatus,
    UserRole,
)
from app.services.refund_service import generate_allocations, generate_installments
from app.services.knowledge_indexer import reindex_all
from app.models.refund import RefundPlan

DEMO_PASSWORD = "demo1234"

SECTORS = [
    ("Agriculture", "Petits agriculteurs et producteurs locaux"),
    ("Élevage", "Éleveurs locaux"),
    ("Artisanat", "Artisans et savoir-faire traditionnel"),
    ("Commerce", "Petits commerçants"),
]

# Tables métier vidées par --reset, dans l'ordre inverse des dépendances
RESET_TABLES = [
    "investment_refund_allocations",
    "refund_installments",
    "refund_plans",
    "ai_analysis_reports",
    "chat_messages",
    "chat_conversations",
    "notifications",
    "documents",
    "investments",
    "projects",
    "users",
]


def reset(db):
    print("Vidage des tables métier...")
    db.execute(text("TRUNCATE " + ", ".join(RESET_TABLES) + " RESTART IDENTITY CASCADE"))
    db.commit()


def get_or_create_sectors(db) -> dict[str, int]:
    for name, description in SECTORS:
        if not db.query(Sector).filter(Sector.name == name).first():
            db.add(Sector(name=name, description=description))
    db.commit()
    return {s.name: s.id for s in db.query(Sector).all()}


def create_users(db) -> dict[str, User]:
    specs = [
        ("porteur@demo.ma", "Fatima Ait Souala", UserRole.PORTEUR, "Essaouira", "Marrakech-Safi"),
        ("porteur2@demo.ma", "Hassan El Mansouri", UserRole.PORTEUR, "Taliouine", "Souss-Massa"),
        ("investisseur@demo.ma", "Sara Bennani", UserRole.INVESTISSEUR, "Casablanca", "Casablanca-Settat"),
        ("investisseur2@demo.ma", "Youssef Idrissi", UserRole.INVESTISSEUR, "Rabat", "Rabat-Salé-Kénitra"),
        ("admin@demo.ma", "Administrateur", UserRole.ADMIN, "Rabat", "Rabat-Salé-Kénitra"),
    ]
    users = {}
    for email, full_name, role, city, region in specs:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                full_name=full_name,
                role=role,
                city=city,
                region=region,
                is_verified=True,
            )
            db.add(user)
        users[email] = user
    db.commit()
    return users


def create_projects(db, users, sectors) -> dict[str, Project]:
    now = datetime.now(timezone.utc)
    specs = [
        dict(
            key="argane",
            owner="porteur@demo.ma",
            sector="Agriculture",
            title="Coopérative Argane Ait Souala",
            description=(
                "Notre coopérative réunit 12 femmes d'un village proche d'Essaouira. "
                "Nous extrayons l'huile d'argan à la meule de pierre, selon la méthode "
                "traditionnelle. Le financement permettra d'acheter une presse mécanique "
                "afin de doubler notre capacité et de réduire la pénibilité du travail."
            ),
            amount_requested=40000,
            amount_raised=40000,
            status=ProjectStatus.EN_REMBOURSEMENT,
            city="Essaouira",
            region="Marrakech-Safi",
        ),
        dict(
            key="safran",
            owner="porteur2@demo.ma",
            sector="Agriculture",
            title="Safran de Taliouine",
            description=(
                "Exploitation familiale de safran sur les hauteurs de Taliouine. "
                "Le financement servira à étendre la parcelle d'un hectare et à installer "
                "un système d'irrigation goutte-à-goutte économe en eau."
            ),
            amount_requested=50000,
            amount_raised=22500,
            status=ProjectStatus.EN_FINANCEMENT,
            city="Taliouine",
            region="Souss-Massa",
        ),
        dict(
            key="tapis",
            owner="porteur@demo.ma",
            sector="Artisanat",
            title="Tapis d'Azilal — Coopérative Tiwizi",
            description=(
                "Huit artisanes tisseuses perpétuant les motifs berbères d'Azilal. "
                "Le financement permettra d'acheter de la laine en gros et deux métiers "
                "à tisser supplémentaires."
            ),
            amount_requested=30000,
            amount_raised=0,
            status=ProjectStatus.VALIDE,
            city="Azilal",
            region="Béni Mellal-Khénifra",
        ),
        dict(
            key="chevres",
            owner="porteur2@demo.ma",
            sector="Élevage",
            title="Élevage caprin et fromagerie de Chefchaouen",
            description=(
                "Petit élevage de chèvres dans le Rif, avec transformation fromagère "
                "artisanale. Le financement couvre l'achat de dix chèvres laitières et "
                "l'aménagement d'une chambre d'affinage."
            ),
            amount_requested=25000,
            amount_raised=0,
            status=ProjectStatus.A_VALIDER,
            city="Chefchaouen",
            region="Tanger-Tétouan-Al Hoceïma",
        ),
        dict(
            key="poterie",
            owner="porteur@demo.ma",
            sector="Artisanat",
            title="Atelier de poterie de Safi",
            description=(
                "Atelier familial de poterie émaillée dans la médina de Safi. "
                "Projet de rénovation du four traditionnel."
            ),
            amount_requested=18000,
            amount_raised=0,
            status=ProjectStatus.BROUILLON,
            city="Safi",
            region="Marrakech-Safi",
        ),
        dict(
            key="epicerie",
            owner="porteur2@demo.ma",
            sector="Commerce",
            title="Épicerie solidaire de Zagora",
            description=(
                "Épicerie de quartier tenue par une association de femmes de Zagora, "
                "proposant des produits locaux (dattes, huile d'olive, légumineuses) "
                "à prix juste, en circuit court avec les coopératives agricoles de la "
                "région. Le financement permettra d'aménager le local et de constituer "
                "un premier stock."
            ),
            amount_requested=22000,
            amount_raised=0,
            status=ProjectStatus.VALIDE,
            city="Zagora",
            region="Drâa-Tafilalet",
        ),
        dict(
            key="miel",
            owner="porteur@demo.ma",
            sector="Agriculture",
            title="Miellerie de l'Atlas — Aït Bouguemez",
            description=(
                "Coopérative apicole de la vallée d'Aït Bouguemez, produisant un miel "
                "de montagne (thym, lavande sauvage) en ruches traditionnelles. Le "
                "financement permettra d'acquérir 40 ruches supplémentaires et du "
                "matériel d'extraction certifié bio, pour tripler la production annuelle."
            ),
            amount_requested=32000,
            amount_raised=0,
            status=ProjectStatus.SOUMIS,
            city="Aït Bouguemez",
            region="Béni Mellal-Khénifra",
        ),
    ]

    projects = {}
    for i, spec in enumerate(specs):
        key = spec.pop("key")
        owner_email = spec.pop("owner")
        sector_name = spec.pop("sector")
        existing = db.query(Project).filter(Project.title == spec["title"]).first()
        if existing:
            projects[key] = existing
            continue
        project = Project(
            id=uuid.uuid4(),
            owner_id=users[owner_email].id,
            sector_id=sectors[sector_name],
            created_at=now - timedelta(days=60 - i * 10),
            **spec,
        )
        if project.status != ProjectStatus.BROUILLON:
            project.submitted_at = now - timedelta(days=55 - i * 10)
        if project.status in (
            ProjectStatus.VALIDE,
            ProjectStatus.EN_FINANCEMENT,
            ProjectStatus.FINANCE,
            ProjectStatus.EN_REMBOURSEMENT,
        ):
            project.validated_at = now - timedelta(days=50 - i * 10)
        db.add(project)
        projects[key] = project
    db.commit()
    return projects


def create_ai_reports(db, projects, users):
    """Rapports de l'IA agentique : un dossier propre, un dossier à examiner."""
    specs = [
        (
            "chevres",
            78.0,
            22.0,
            AnalysisVerdict.A_EXAMINER,
            [
                {
                    "type": "document_manquant",
                    "severite": "moyenne",
                    "description": "Aucun devis fourni pour l'achat des chèvres laitières.",
                },
                {
                    "type": "coherence_montant",
                    "severite": "faible",
                    "description": "Le montant demandé est cohérent avec les prix du marché local.",
                },
            ],
        ),
        (
            "tapis",
            88.0,
            8.0,
            AnalysisVerdict.RECOMMANDE,
            [
                {
                    "type": "dossier_complet",
                    "severite": "faible",
                    "description": "Pièces justificatives complètes et cohérentes entre elles.",
                }
            ],
        ),
    ]
    for key, relevance, fraud, verdict, findings in specs:
        project = projects[key]
        if db.query(AIAnalysisReport).filter(AIAnalysisReport.project_id == project.id).first():
            continue
        report = AIAnalysisReport(
            id=uuid.uuid4(),
            project_id=project.id,
            relevance_score=relevance,
            fraud_risk_score=fraud,
            verdict=verdict,
            findings=findings,
            raw_model_output={"note": "rapport de démonstration"},
        )
        # Le dossier « tapis » a déjà été revu par l'admin
        if key == "tapis":
            report.reviewed_by_admin_id = users["admin@demo.ma"].id
            report.admin_decision = ProjectStatus.VALIDE
            report.admin_notes = "Dossier solide, coopérative déjà connue."
            report.reviewed_at = datetime.now(timezone.utc)
        db.add(report)
    db.commit()


def create_investments(db, projects, users) -> list[Investment]:
    now = datetime.now(timezone.utc)
    specs = [
        ("argane", "investisseur@demo.ma", 25000),
        ("argane", "investisseur2@demo.ma", 15000),
        ("safran", "investisseur@demo.ma", 12500),
        ("safran", "investisseur2@demo.ma", 10000),
    ]
    created = []
    for key, email, amount in specs:
        project = projects[key]
        investor = users[email]
        existing = (
            db.query(Investment)
            .filter(Investment.project_id == project.id, Investment.investor_id == investor.id)
            .first()
        )
        if existing:
            created.append(existing)
            continue
        inv = Investment(
            id=uuid.uuid4(),
            project_id=project.id,
            investor_id=investor.id,
            amount=amount,
            status=InvestmentStatus.CONFIRME,
            share_contact_consent=True,
            invested_at=now - timedelta(days=30),
        )
        db.add(inv)
        created.append(inv)
    db.commit()
    return created


def create_refund_plan(db, projects):
    """Plan de remboursement en nature pour le projet déjà financé."""
    project = projects["argane"]
    if db.query(RefundPlan).filter(RefundPlan.project_id == project.id).first():
        return
    plan = RefundPlan(
        id=uuid.uuid4(),
        project_id=project.id,
        product_description="Huile d'argan alimentaire bio",
        unit="litre",
        total_quantity=120,
        installments_count=6,
        frequency="mensuel",
        start_date=date.today() - timedelta(days=60),
    )
    db.add(plan)
    db.flush()
    installments = generate_installments(db, plan)
    generate_allocations(db, project.id, installments)
    db.commit()

    # Marque les deux premières échéances comme livrées
    from app.models.enums import InstallmentStatus
    from app.models.refund import InvestmentRefundAllocation

    for inst in installments[:2]:
        inst.status = InstallmentStatus.LIVRE
        inst.quantity_delivered = inst.quantity_due
        inst.delivered_at = datetime.now(timezone.utc)
        for alloc in (
            db.query(InvestmentRefundAllocation)
            .filter(InvestmentRefundAllocation.installment_id == inst.id)
            .all()
        ):
            alloc.status = InstallmentStatus.LIVRE
            alloc.delivered_at = datetime.now(timezone.utc)
    db.commit()


def main():
    should_reset = "--reset" in sys.argv
    db = SessionLocal()
    try:
        if should_reset:
            reset(db)

        sectors = get_or_create_sectors(db)
        users = create_users(db)
        projects = create_projects(db, users, sectors)
        create_ai_reports(db, projects, users)
        create_investments(db, projects, users)
        create_refund_plan(db, projects)

        # Indexe la base de connaissances (RAG du chat) sur les données
        # de démo fraîchement créées : projets publics, secteurs, FAQ.
        reindex_all(db)

        print("\nDonnées de démonstration créées.")
        print(f"  {len(users)} utilisateurs, {len(projects)} projets")
        print(f"\nMot de passe pour tous les comptes : {DEMO_PASSWORD}")
        for email in users:
            print(f"  - {email}")
        print("\nÀ voir dans l'interface :")
        print("  · porteur@demo.ma        -> 3 dossiers (brouillon, validé, en remboursement)")
        print("  · investisseur@demo.ma   -> portefeuille + suivi de livraisons en nature")
        print("  · admin@demo.ma          -> 1 dossier en attente avec rapport d'analyse IA")
    finally:
        db.close()


if __name__ == "__main__":
    main()
