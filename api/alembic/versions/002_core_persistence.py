"""Core persistence tables for AI Venture Studio.

Revision ID: 002_core_persistence
Revises: 001_extensions
Create Date: 2026-06-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "002_core_persistence"
down_revision: Union[str, None] = "001_extensions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TIMESTAMP_TABLES = (
    "sources",
    "signals",
    "categories",
    "complaints",
    "opportunities",
    "opportunity_scores",
    "reports",
)

CATEGORY_SEEDS: list[tuple[str, str, str, str]] = [
    ("pricing", "Pricing", "Cost, billing, or pricing model frustration", "complaint_category"),
    ("integration", "Integration", "Missing or broken integrations", "complaint_category"),
    ("ux_ui", "UX / UI", "Usability and interface problems", "complaint_category"),
    ("performance", "Performance", "Speed, reliability, or scale issues", "complaint_category"),
    ("support", "Support", "Customer support experience", "complaint_category"),
    ("missing_feature", "Missing Feature", "Capability gap in existing tools", "complaint_category"),
    ("workflow", "Workflow", "Process or workflow friction", "complaint_category"),
    ("data_export", "Data Export", "Import, export, or portability issues", "complaint_category"),
    ("onboarding", "Onboarding", "Setup and getting-started pain", "complaint_category"),
    ("security", "Security", "Security, privacy, or compliance concerns", "complaint_category"),
    ("other", "Other", "Uncategorized complaint theme", "complaint_category"),
    ("saas_b2b", "SaaS B2B", "Business software market", "domain"),
    ("saas_b2c", "SaaS B2C", "Consumer software market", "domain"),
    ("ecommerce", "E-commerce", "Online retail and commerce", "domain"),
    ("devtools", "Developer Tools", "Tools for builders and engineers", "domain"),
    ("fintech", "Fintech", "Financial technology", "domain"),
    ("healthcare", "Healthcare", "Healthcare and wellness", "domain"),
    ("education", "Education", "Education and learning", "domain"),
    ("hr_recruiting", "HR & Recruiting", "People operations and hiring", "domain"),
    ("marketing", "Marketing", "Marketing and growth", "domain"),
    ("ops_it", "Ops & IT", "Operations and IT administration", "domain"),
    ("creator_economy", "Creator Economy", "Creators and independent builders", "domain"),
    ("founder", "Founder", "Startup founder persona", "persona"),
    ("developer", "Developer", "Software developer persona", "persona"),
    ("product_manager", "Product Manager", "Product manager persona", "persona"),
    ("ops_admin", "Ops / Admin", "Operations administrator persona", "persona"),
    ("marketer", "Marketer", "Marketing professional persona", "persona"),
    ("sales", "Sales", "Sales professional persona", "persona"),
    ("support_agent", "Support Agent", "Customer support persona", "persona"),
    ("consumer", "Consumer", "End consumer persona", "persona"),
]


def _create_updated_at_trigger(table: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER trg_{table}_updated_at
        BEFORE UPDATE ON {table}
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_sources_enabled",
        "sources",
        ["enabled"],
        unique=False,
        postgresql_where=sa.text("enabled = true"),
    )

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "kind", name="uq_categories_code_kind"),
    )
    op.create_index("idx_categories_kind", "categories", ["kind"], unique=False)

    op.create_table(
        "signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("processing_status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("skip_reason", sa.Text(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_signals_source_external"),
    )
    op.create_index("idx_signals_status_collected", "signals", ["processing_status", "collected_at"], unique=False)
    op.create_index("idx_signals_published", "signals", ["published_at"], unique=False)

    op.create_table(
        "complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("persona_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("verbatim_quote", sa.Text(), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("product_mentions", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("llm_model", sa.String(length=50), nullable=False),
        sa.Column("llm_confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("severity >= 1 AND severity <= 5", name="ck_complaints_severity"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["domain_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["persona_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("signal_id"),
    )
    op.create_index("idx_complaints_category_domain", "complaints", ["category_id", "domain_id"], unique=False)
    op.create_index("idx_complaints_severity", "complaints", ["severity"], unique=False)

    op.create_table(
        "opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("problem_statement", sa.Text(), nullable=False),
        sa.Column("target_user", sa.Text(), nullable=False),
        sa.Column("frequency_signal", sa.Text(), nullable=False),
        sa.Column("existing_alternatives", sa.Text(), nullable=False),
        sa.Column("gap", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("review_status", sa.String(length=30), server_default="new", nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="ck_opportunities_confidence"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_opportunities_review_status", "opportunities", ["review_status", "created_at"], unique=False)
    op.create_index("idx_opportunities_confidence", "opportunities", [sa.text("confidence_score DESC")], unique=False)

    op.create_table(
        "opportunity_complaints",
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("complaint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("opportunity_id", "complaint_id"),
    )

    op.create_table(
        "opportunity_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("frequency_score", sa.Float(), nullable=False),
        sa.Column("severity_score", sa.Float(), nullable=False),
        sa.Column("evidence_score", sa.Float(), nullable=False),
        sa.Column("scoring_model", sa.String(length=50), nullable=False),
        sa.Column("scoring_notes", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("overall_score >= 0 AND overall_score <= 1", name="ck_opportunity_scores_overall"),
        sa.CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="ck_opportunity_scores_confidence"),
        sa.CheckConstraint("frequency_score >= 0 AND frequency_score <= 1", name="ck_opportunity_scores_frequency"),
        sa.CheckConstraint("severity_score >= 0 AND severity_score <= 1", name="ck_opportunity_scores_severity"),
        sa.CheckConstraint("evidence_score >= 0 AND evidence_score <= 1", name="ck_opportunity_scores_evidence"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_opportunity_scores_opportunity",
        "opportunity_scores",
        ["opportunity_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_opportunity_scores_current",
        "opportunity_scores",
        ["opportunity_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index(
        "idx_opportunity_scores_overall",
        "opportunity_scores",
        [sa.text("overall_score DESC")],
        unique=False,
    )

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_reports_type_status", "reports", ["report_type", "status"], unique=False)
    op.create_index("idx_reports_opportunity", "reports", ["opportunity_id"], unique=False)

    for table in TIMESTAMP_TABLES:
        _create_updated_at_trigger(table)

    categories = sa.table(
        "categories",
        sa.column("code", sa.String),
        sa.column("label", sa.String),
        sa.column("description", sa.Text),
        sa.column("kind", sa.String),
    )
    op.bulk_insert(
        categories,
        [
            {"code": code, "label": label, "description": description, "kind": kind}
            for code, label, description, kind in CATEGORY_SEEDS
        ],
    )


def downgrade() -> None:
    for table in reversed(TIMESTAMP_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")

    op.drop_table("reports")
    op.drop_table("opportunity_scores")
    op.drop_table("opportunity_complaints")
    op.drop_table("opportunities")
    op.drop_table("complaints")
    op.drop_table("signals")
    op.drop_table("categories")
    op.drop_table("sources")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
