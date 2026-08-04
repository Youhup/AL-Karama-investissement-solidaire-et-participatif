import json

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.ai_report import AIAnalysisReport
from app.models.enums import AnalysisVerdict, ProjectStatus
from app.models.project import Project
from app.models.project_fund_usage import ProjectFundUsageItem
from app.services.agentic_analysis.tools import (
    TOOL_REGISTRY,
    TOOLS_SCHEMA,
    get_project_documents_text,
)
from app.services.groq_client import chat_completion

SYSTEM_PROMPT = """Tu es un agent d'analyse de dossiers pour une plateforme
de crowdfunding solidaire (ESS) au Maroc. Ton rôle :
1. Évaluer la pertinence du projet (cohérence, sérieux, faisabilité).
2. Identifier les failles ou informations manquantes dans le dossier.
3. Détecter des signaux de fraude potentiels (montants incohérents,
   dossiers dupliqués, informations contradictoires).
4. Croiser les déclarations structurées du porteur (statut juridique,
   impact social, financement antérieur, facteurs de risque déclarés)
   avec la description libre et les documents joints : signale toute
   incohérence entre ce qui est déclaré et ce qui est démontré.

Utilise les outils disponibles pour vérifier les faits avant de conclure.
Termine TOUJOURS ta réponse finale par un objet JSON strict avec les clés :
relevance_score (0-100), fraud_risk_score (0-100),
verdict ("recommande" | "a_examiner" | "suspect" | "rejete_suggere"),
findings (liste d'objets {type, severite, description})."""


def _format_project_context(project: Project, fund_usage_items: list[ProjectFundUsageItem]) -> str:
    """Construit le contexte structuré du dossier (formulaire enrichi),
    en plus de la description libre, pour que l'agent puisse croiser ces
    déclarations avec les documents et ses tools (montant, doublons)."""
    lines = [
        f"Titre: {project.title}",
        f"Montant demandé: {project.amount_requested} {project.currency}",
        f"Durée de financement: {project.funding_duration_days} jours",
    ]
    if project.project_stage:
        lines.append(f"Étape du projet: {project.project_stage.value}")
    if project.legal_status:
        lines.append(f"Statut juridique: {project.legal_status.value}")
    if project.legal_id_number:
        lines.append(f"Numéro d'identification légale: {project.legal_id_number}")
    if project.activity_start_year:
        lines.append(f"Année de début d'activité: {project.activity_start_year}")
    if project.target_beneficiaries:
        lines.append(f"Bénéficiaires ciblés: {', '.join(project.target_beneficiaries)}")
    lines.append(f"Emplois créés: {project.jobs_created}")
    lines.append(f"Emplois maintenus: {project.jobs_maintained}")
    if project.social_impact_description:
        lines.append(f"Impact social déclaré:\n{project.social_impact_description}")
    lines.append(f"Financement antérieur déclaré: {'oui' if project.previous_funding else 'non'}")
    if project.previous_funding_details:
        lines.append(f"Détails du financement antérieur:\n{project.previous_funding_details}")
    if project.risk_factors:
        lines.append(f"Facteurs de risque déclarés par le porteur:\n{project.risk_factors}")
    if project.pitch_summary:
        lines.append(f"Résumé (pitch): {project.pitch_summary}")
    if project.references_text:
        lines.append(f"Références citées par le porteur:\n{project.references_text}")

    if fund_usage_items:
        usage_lines = "\n".join(
            f"- {item.category}: {item.amount} {project.currency}"
            + (f" ({item.description})" if item.description else "")
            for item in fund_usage_items
        )
        lines.append(f"Répartition déclarée du montant demandé par poste:\n{usage_lines}")

    lines.append(f"\nDescription complète:\n{project.description}")
    return "\n".join(lines)


def _run_agent_loop(
    project_id: str,
    project: Project,
    fund_usage_items: list[ProjectFundUsageItem],
    documents_text: str,
) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"project_id: {project_id}\n\n"
                f"Dossier du projet:\n{_format_project_context(project, fund_usage_items)}\n\n"
                f"Texte extrait des documents joints:\n{documents_text[:6000]}"
            ),
        },
    ]

    # Boucle de tool calling (max 5 itérations de sécurité)
    for _ in range(5):
        message = chat_completion(messages, model=settings.GROQ_AGENT_MODEL, tools=TOOLS_SCHEMA)

        if not message.tool_calls:
            # Le modèle a produit sa réponse finale -> on extrait le JSON
            return _extract_json(message.content)

        messages.append({"role": "assistant", "content": message.content, "tool_calls": message.tool_calls})

        for call in message.tool_calls:
            fn = TOOL_REGISTRY[call.function.name]
            args = json.loads(call.function.arguments)
            # project_id vient de l'argument généré par le modèle, qui peut
            # le tronquer/halluciner (ex: UUID coupé suivi de "..."). On
            # impose donc toujours le vrai project_id du dossier en cours
            # d'analyse plutôt que de faire confiance au LLM.
            args["project_id"] = project_id
            with SessionLocal() as db:
                result = fn(db=db, **args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                }
            )

    return {
        "relevance_score": 0,
        "fraud_risk_score": 100,
        "verdict": "a_examiner",
        "findings": [{"type": "analyse_incomplete", "severite": "haute", "description": "Nombre max d'itérations atteint"}],
    }


def _extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


@celery_app.task(name="trigger_project_analysis")
def trigger_project_analysis(project_id: str):
    """Tâche asynchrone : appelée quand un porteur soumet son dossier."""
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        project.status = ProjectStatus.EN_ANALYSE
        db.commit()

        documents_text = get_project_documents_text(db, project_id)
        fund_usage_items = (
            db.query(ProjectFundUsageItem)
            .filter(ProjectFundUsageItem.project_id == project_id)
            .order_by(ProjectFundUsageItem.created_at)
            .all()
        )
        result = _run_agent_loop(project_id, project, fund_usage_items, documents_text)

        # Si l'admin a tranché avant la fin de cette analyse, decide() a déjà
        # créé une ligne (verdict=None) pour porter sa décision : on la
        # complète au lieu d'en créer une nouvelle, sinon la décision de
        # l'admin devient orpheline et il faut la retrouver en même temps
        # que l'ancienne ligne pour ne pas la perdre.
        report = (
            db.query(AIAnalysisReport)
            .filter(AIAnalysisReport.project_id == project_id, AIAnalysisReport.verdict.is_(None))
            .order_by(AIAnalysisReport.analyzed_at.desc())
            .first()
        )
        if report is None:
            report = AIAnalysisReport(project_id=project.id)
            db.add(report)

        report.relevance_score = result.get("relevance_score")
        report.fraud_risk_score = result.get("fraud_risk_score")
        report.verdict = AnalysisVerdict(result.get("verdict", "a_examiner"))
        report.findings = result.get("findings", [])
        report.raw_model_output = result

        # Ne pas écraser une décision déjà prise par l'admin sur ce rapport
        # pendant que l'analyse tournait.
        if report.admin_decision is None:
            project.status = ProjectStatus.A_VALIDER
        db.commit()
