"""Add 0-100 score and dimension columns to opportunity_scores.

Revision ID: 005_opportunity_score_dimensions
Revises: 004_llm_calls
Create Date: 2026-06-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_opportunity_score_dimensions"
down_revision: Union[str, None] = "004_llm_calls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("opportunity_scores", sa.Column("score", sa.Integer(), nullable=True))
    op.add_column("opportunity_scores", sa.Column("volume_score", sa.Float(), nullable=True))
    op.add_column(
        "opportunity_scores",
        sa.Column("market_indicator_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "opportunity_scores",
        sa.Column("implementation_ease_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "opportunity_scores",
        sa.Column("founder_fit_score", sa.Float(), nullable=True),
    )

    op.execute(
        """
        UPDATE opportunity_scores
        SET score = LEAST(100, GREATEST(0, ROUND(overall_score * 100))),
            volume_score = frequency_score,
            market_indicator_score = evidence_score,
            implementation_ease_score = 0.5,
            founder_fit_score = 0.5
        WHERE score IS NULL
        """
    )

    op.alter_column("opportunity_scores", "score", nullable=False)
    op.alter_column("opportunity_scores", "volume_score", nullable=False)
    op.alter_column("opportunity_scores", "market_indicator_score", nullable=False)
    op.alter_column("opportunity_scores", "implementation_ease_score", nullable=False)
    op.alter_column("opportunity_scores", "founder_fit_score", nullable=False)

    op.create_check_constraint(
        "ck_opportunity_scores_score",
        "opportunity_scores",
        "score >= 0 AND score <= 100",
    )
    op.create_check_constraint(
        "ck_opportunity_scores_volume",
        "opportunity_scores",
        "volume_score >= 0 AND volume_score <= 1",
    )
    op.create_check_constraint(
        "ck_opportunity_scores_market",
        "opportunity_scores",
        "market_indicator_score >= 0 AND market_indicator_score <= 1",
    )
    op.create_check_constraint(
        "ck_opportunity_scores_implementation",
        "opportunity_scores",
        "implementation_ease_score >= 0 AND implementation_ease_score <= 1",
    )
    op.create_check_constraint(
        "ck_opportunity_scores_founder_fit",
        "opportunity_scores",
        "founder_fit_score >= 0 AND founder_fit_score <= 1",
    )
    op.create_index(
        "idx_opportunity_scores_score",
        "opportunity_scores",
        [sa.text("score DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_opportunity_scores_score", table_name="opportunity_scores")
    op.drop_constraint("ck_opportunity_scores_founder_fit", "opportunity_scores", type_="check")
    op.drop_constraint("ck_opportunity_scores_implementation", "opportunity_scores", type_="check")
    op.drop_constraint("ck_opportunity_scores_market", "opportunity_scores", type_="check")
    op.drop_constraint("ck_opportunity_scores_volume", "opportunity_scores", type_="check")
    op.drop_constraint("ck_opportunity_scores_score", "opportunity_scores", type_="check")
    op.drop_column("opportunity_scores", "founder_fit_score")
    op.drop_column("opportunity_scores", "implementation_ease_score")
    op.drop_column("opportunity_scores", "market_indicator_score")
    op.drop_column("opportunity_scores", "volume_score")
    op.drop_column("opportunity_scores", "score")
