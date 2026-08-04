"""add dossier fields (stage/legal/impact/trust/pitch), fund usage items, refund tiers

Revision ID: b2f6c9d1a3e5
Revises: f3c9a1d2e4b7
Create Date: 2026-08-02 00:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2f6c9d1a3e5'
down_revision: Union[str, None] = 'f3c9a1d2e4b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Montant minimum d'investissement de la plateforme — fixe le plancher du
# premier (et ici unique) palier reconstitué pour les plans existants.
PLATFORM_MIN_INVESTMENT = 100


def upgrade() -> None:
    # op.add_column, contrairement à op.create_table, ne crée pas
    # automatiquement le type ENUM Postgres référencé par la colonne — il
    # faut l'émettre explicitement avant l'ALTER TABLE (sinon
    # « type ... does not exist »).
    project_stage_enum = postgresql.ENUM(
        'idee', 'demarrage', 'croissance', name='project_stage'
    )
    project_stage_enum.create(op.get_bind(), checkfirst=True)

    legal_status_enum = postgresql.ENUM(
        'auto_entrepreneur', 'cooperative', 'association', 'sarl', 'informel', 'autre',
        name='legal_status',
    )
    legal_status_enum.create(op.get_bind(), checkfirst=True)

    # --- Étape 1 : étape actuelle du projet ---
    op.add_column('projects', sa.Column(
        'project_stage',
        postgresql.ENUM('idee', 'demarrage', 'croissance', name='project_stage', create_type=False),
        nullable=True,
    ))

    # --- Section A : statut juridique et identité ---
    op.add_column('projects', sa.Column(
        'legal_status',
        postgresql.ENUM(
            'auto_entrepreneur', 'cooperative', 'association', 'sarl', 'informel', 'autre',
            name='legal_status', create_type=False,
        ),
        nullable=True,
    ))
    op.add_column('projects', sa.Column('legal_id_number', sa.String(length=50), nullable=True))
    op.add_column('projects', sa.Column('activity_start_year', sa.Integer(), nullable=True))

    # --- Section D : impact social ---
    op.add_column(
        'projects',
        sa.Column('target_beneficiaries', postgresql.ARRAY(sa.String(length=30)), nullable=True),
    )
    op.add_column('projects', sa.Column('jobs_created', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('projects', sa.Column('jobs_maintained', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('projects', sa.Column('social_impact_description', sa.Text(), nullable=True))

    # --- Section E : confiance et historique ---
    op.add_column(
        'projects', sa.Column('previous_funding', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('projects', sa.Column('previous_funding_details', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('risk_factors', sa.Text(), nullable=True))

    # --- Section F : présentation ---
    op.add_column('projects', sa.Column('pitch_summary', sa.String(length=140), nullable=True))
    op.add_column('projects', sa.Column('references_text', sa.Text(), nullable=True))

    # --- Section B : utilisation des fonds ---
    op.create_table(
        'project_fund_usage_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('category', sa.String(length=120), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- Section C : remboursement en nature par paliers ---
    # RefundPlan devient un simple en-tête ; le détail (produit, quantité,
    # fréquence) migre sur RefundTier, un plan pouvant désormais proposer
    # plusieurs contreparties différentes selon la tranche de montant investi
    # (ex. œufs pour les petits montants, poule pour les plus gros).
    repayment_frequency_enum = postgresql.ENUM(
        'hebdomadaire', 'mensuelle', 'trimestrielle', 'unique', 'a_la_recolte',
        name='repayment_frequency',
    )
    repayment_frequency_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'refund_tiers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('refund_plan_id', sa.UUID(), nullable=False),
        sa.Column('tier_min_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tier_max_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('product_description', sa.String(length=255), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=False),
        sa.Column('quantity_per_occurrence', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column(
            'frequency',
            postgresql.ENUM(
                'hebdomadaire', 'mensuelle', 'trimestrielle', 'unique', 'a_la_recolte',
                name='repayment_frequency', create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('installments_count', sa.Integer(), nullable=False),
        sa.Column('estimated_unit_value', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['refund_plan_id'], ['refund_plans.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Données existantes : tout RefundPlan déjà créé (démo ou réel) avait un
    # unique produit réparti au prorata entre investisseurs. On le reproduit
    # fidèlement en un unique palier ouvert (100 MAD et plus, sans plafond),
    # pour ne perdre ni l'historique des livraisons déjà effectuées ni les
    # allocations existantes — seule la structure change, pas les données.
    bind = op.get_bind()
    old_frequency_map = {'mensuel': 'mensuelle', 'trimestriel': 'trimestrielle'}
    existing_plans = bind.execute(sa.text(
        'SELECT id, product_description, unit, total_quantity, installments_count, frequency FROM refund_plans'
    )).mappings().all()

    plan_to_tier = {}
    for plan in existing_plans:
        tier_id = uuid.uuid4()
        plan_to_tier[plan['id']] = tier_id
        quantity_per_occurrence = float(plan['total_quantity']) / plan['installments_count']
        bind.execute(
            sa.text(
                'INSERT INTO refund_tiers '
                '(id, refund_plan_id, tier_min_amount, tier_max_amount, product_description, unit, '
                ' quantity_per_occurrence, frequency, installments_count, estimated_unit_value) '
                'VALUES '
                '(:id, :plan_id, :tier_min, NULL, :product_description, :unit, '
                ' :quantity_per_occurrence, :frequency, :installments_count, NULL)'
            ),
            {
                'id': tier_id,
                'plan_id': plan['id'],
                'tier_min': PLATFORM_MIN_INVESTMENT,
                'product_description': plan['product_description'],
                'unit': plan['unit'],
                'quantity_per_occurrence': quantity_per_occurrence,
                'frequency': old_frequency_map.get(plan['frequency'], 'mensuelle'),
                'installments_count': plan['installments_count'],
            },
        )

    op.add_column('refund_installments', sa.Column('refund_tier_id', sa.UUID(), nullable=True))
    for plan_id, tier_id in plan_to_tier.items():
        bind.execute(
            sa.text('UPDATE refund_installments SET refund_tier_id = :tier_id WHERE refund_plan_id = :plan_id'),
            {'tier_id': tier_id, 'plan_id': plan_id},
        )

    op.drop_constraint(
        'refund_installments_refund_plan_id_installment_number_key', 'refund_installments', type_='unique'
    )
    op.drop_constraint('refund_installments_refund_plan_id_fkey', 'refund_installments', type_='foreignkey')
    op.drop_column('refund_installments', 'refund_plan_id')
    op.alter_column('refund_installments', 'refund_tier_id', existing_type=sa.UUID(), nullable=False)
    op.create_foreign_key(
        'refund_installments_refund_tier_id_fkey', 'refund_installments', 'refund_tiers',
        ['refund_tier_id'], ['id'],
    )
    op.create_unique_constraint(
        'refund_installments_refund_tier_id_installment_number_key',
        'refund_installments', ['refund_tier_id', 'installment_number'],
    )

    op.drop_column('refund_plans', 'product_description')
    op.drop_column('refund_plans', 'unit')
    op.drop_column('refund_plans', 'total_quantity')
    op.drop_column('refund_plans', 'installments_count')
    op.drop_column('refund_plans', 'frequency')
    op.alter_column('refund_plans', 'start_date', existing_type=sa.Date(), nullable=False)


def downgrade() -> None:
    # Reconstitution best-effort : correcte pour tout plan resté à un seul
    # palier (le cas de tout plan créé avant cette migration, ou après elle
    # sans avoir utilisé plusieurs paliers). Un plan à plusieurs paliers ne
    # peut pas revenir sans perte au modèle « un seul produit » — seul le
    # premier palier (le plus petit tier_min_amount) est repris, et la
    # contrainte d'unicité (refund_plan_id, installment_number) peut échouer
    # si plusieurs paliers du même plan partagent des numéros d'échéance.
    new_frequency_map = {'mensuelle': 'mensuel', 'trimestrielle': 'trimestriel'}

    op.add_column('refund_plans', sa.Column('product_description', sa.String(length=255), nullable=True))
    op.add_column('refund_plans', sa.Column('unit', sa.String(length=50), nullable=True))
    op.add_column('refund_plans', sa.Column('total_quantity', sa.Numeric(precision=12, scale=3), nullable=True))
    op.add_column('refund_plans', sa.Column('installments_count', sa.Integer(), nullable=True))
    op.add_column('refund_plans', sa.Column('frequency', sa.String(length=20), nullable=True))

    bind = op.get_bind()
    first_tiers = bind.execute(sa.text(
        'SELECT DISTINCT ON (refund_plan_id) id, refund_plan_id, product_description, unit, '
        '       quantity_per_occurrence, frequency, installments_count '
        'FROM refund_tiers ORDER BY refund_plan_id, tier_min_amount'
    )).mappings().all()

    tier_to_plan_defaults = {}
    for tier in first_tiers:
        tier_to_plan_defaults[tier['id']] = tier['refund_plan_id']
        bind.execute(
            sa.text(
                'UPDATE refund_plans SET product_description = :product_description, unit = :unit, '
                'total_quantity = :total_quantity, installments_count = :installments_count, '
                'frequency = :frequency WHERE id = :plan_id'
            ),
            {
                'product_description': tier['product_description'],
                'unit': tier['unit'],
                'total_quantity': float(tier['quantity_per_occurrence']) * tier['installments_count'],
                'installments_count': tier['installments_count'],
                'frequency': new_frequency_map.get(tier['frequency'], 'mensuel'),
                'plan_id': tier['refund_plan_id'],
            },
        )

    op.add_column('refund_installments', sa.Column('refund_plan_id', sa.UUID(), nullable=True))
    for tier_id, plan_id in tier_to_plan_defaults.items():
        bind.execute(
            sa.text(
                'UPDATE refund_installments SET refund_plan_id = :plan_id WHERE refund_tier_id = :tier_id'
            ),
            {'plan_id': plan_id, 'tier_id': tier_id},
        )

    op.drop_constraint(
        'refund_installments_refund_tier_id_installment_number_key', 'refund_installments', type_='unique'
    )
    op.drop_constraint('refund_installments_refund_tier_id_fkey', 'refund_installments', type_='foreignkey')
    op.drop_column('refund_installments', 'refund_tier_id')
    op.alter_column('refund_installments', 'refund_plan_id', existing_type=sa.UUID(), nullable=False)
    op.create_foreign_key(
        'refund_installments_refund_plan_id_fkey', 'refund_installments', 'refund_plans',
        ['refund_plan_id'], ['id'],
    )
    op.create_unique_constraint(
        'refund_installments_refund_plan_id_installment_number_key',
        'refund_installments', ['refund_plan_id', 'installment_number'],
    )

    op.alter_column('refund_plans', 'product_description', existing_type=sa.String(length=255), nullable=False)
    op.alter_column('refund_plans', 'unit', existing_type=sa.String(length=50), nullable=False)
    op.alter_column('refund_plans', 'total_quantity', existing_type=sa.Numeric(precision=12, scale=3), nullable=False)
    op.alter_column('refund_plans', 'installments_count', existing_type=sa.Integer(), nullable=False)
    op.alter_column('refund_plans', 'frequency', existing_type=sa.String(length=20), nullable=False)
    op.alter_column('refund_plans', 'start_date', existing_type=sa.Date(), nullable=True)

    op.drop_table('refund_tiers')

    op.drop_table('project_fund_usage_items')

    op.drop_column('projects', 'references_text')
    op.drop_column('projects', 'pitch_summary')
    op.drop_column('projects', 'risk_factors')
    op.drop_column('projects', 'previous_funding_details')
    op.drop_column('projects', 'previous_funding')
    op.drop_column('projects', 'social_impact_description')
    op.drop_column('projects', 'jobs_maintained')
    op.drop_column('projects', 'jobs_created')
    op.drop_column('projects', 'target_beneficiaries')
    op.drop_column('projects', 'activity_start_year')
    op.drop_column('projects', 'legal_id_number')
    op.drop_column('projects', 'legal_status')
    op.drop_column('projects', 'project_stage')

    # Types ENUM Postgres : objets globaux, jamais supprimés automatiquement
    # avec les colonnes — nettoyage explicite pour qu'un upgrade rejoué après
    # ce downgrade ne bute pas sur « type ... already exists ».
    for enum_name in ('repayment_frequency', 'legal_status', 'project_stage'):
        op.execute(f'DROP TYPE IF EXISTS {enum_name}')
