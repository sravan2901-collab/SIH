"""schema_hardening: add evidence_paths, contrast_ratio, severity major, generic_name, country_of_origin

Closes the five schema gaps identified by cross-checking implementation_plan_v2 Gaps section
against the LMPC Problem Statement ID 26034:

  Gap 2  — InspectionReport.evidence_paths JSONB   (Phase 6 evidence photos)
  Gap 3  — Violation.severity enum adds 'major'     (Phase 8 font-height violations)
  Gap 5  — Declaration.contrast_ratio FLOAT         (Phase 7 contrast scoring)
  PS gap — Declaration.field_name enum adds 'generic_name', 'country_of_origin'
  PS gap — RuleConfig rows for generic_name and country_of_origin

Source: Legal Metrology (Packaged Commodities) Rules 2011, Rule 6 — mandatory declarations
  on every pre-packaged commodity include the generic/common name of the commodity and,
  for imported goods, the country of origin.

Revision ID: a1b2c3d4e5f6
Revises: d95af3386181
Create Date: 2026-09-15
"""
from datetime import date
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd95af3386181'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Gap 2 — Add evidence_paths to inspection_reports
    # ------------------------------------------------------------------
    op.add_column(
        'inspection_reports',
        sa.Column(
            'evidence_paths',
            JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment='MinIO keys of inspector-attached evidence photos (Phase 6)',
        ),
    )

    # ------------------------------------------------------------------
    # Gap 5 — Add contrast_ratio to declarations
    # ------------------------------------------------------------------
    op.add_column(
        'declarations',
        sa.Column(
            'contrast_ratio',
            sa.Float(),
            nullable=True,
            comment='WCAG contrast ratio computed by Phase 7 font check task',
        ),
    )

    # ------------------------------------------------------------------
    # Gap 3 — Add 'major' to severity_enum
    # PostgreSQL requires adding enum values outside a transaction block.
    # ------------------------------------------------------------------
    op.execute("ALTER TYPE severity_enum ADD VALUE IF NOT EXISTS 'major'")

    # ------------------------------------------------------------------
    # PS gap — Add 'generic_name' and 'country_of_origin' to field_name_enum
    # ------------------------------------------------------------------
    op.execute("ALTER TYPE field_name_enum ADD VALUE IF NOT EXISTS 'generic_name'")
    op.execute("ALTER TYPE field_name_enum ADD VALUE IF NOT EXISTS 'country_of_origin'")

    # ------------------------------------------------------------------
    # PS gap — Seed RuleConfig rows for the two new fields
    # ------------------------------------------------------------------
    rule_configs_table = sa.table(
        "rule_configs",
        sa.column("rule_id", sa.UUID()),
        sa.column("field_name", sa.String(100)),
        sa.column("mandatory", sa.Boolean()),
        sa.column("regex_pattern", sa.String(500)),
        sa.column("min_font_height_mm", sa.Float()),
        sa.column("placement_zone", sa.String(100)),
        sa.column("language_requirement", sa.String(50)),
        sa.column("version", sa.String(20)),
        sa.column("effective_date", sa.Date()),
    )

    # Remove any pre-existing rows for these fields (idempotent)
    op.execute(
        "DELETE FROM rule_configs WHERE field_name IN "
        "('generic_name', 'country_of_origin')"
    )

    op.bulk_insert(
        rule_configs_table,
        [
            {
                # LMPC Rules 2011, Rule 6(1)(a): generic / common name of commodity —
                # mandatory on every pre-packaged article.
                "rule_id": uuid4(),
                "field_name": "generic_name",
                "mandatory": True,
                "regex_pattern": None,
                "min_font_height_mm": 1.0,
                "placement_zone": "PDP",
                "language_requirement": None,
                "version": "1.0",
                "effective_date": date(2011, 4, 1),
            },
            {
                # LMPC Rules 2011, Rule 6(1)(k): country of origin —
                # mandatory for imported pre-packaged commodities.
                "rule_id": uuid4(),
                "field_name": "country_of_origin",
                "mandatory": True,
                "regex_pattern": None,
                "min_font_height_mm": 1.0,
                "placement_zone": None,
                "language_requirement": None,
                "version": "1.0",
                "effective_date": date(2011, 4, 1),
            },
        ],
    )


def downgrade() -> None:
    # Remove seeded rows
    op.execute(
        "DELETE FROM rule_configs WHERE field_name IN "
        "('generic_name', 'country_of_origin')"
    )

    # Remove added columns
    op.drop_column('declarations', 'contrast_ratio')
    op.drop_column('inspection_reports', 'evidence_paths')

    # NOTE: PostgreSQL does not support DROP VALUE from an enum type.
    # The severity_enum 'major' value and the two field_name_enum values
    # cannot be removed without recreating the type.
    # Downgrade leaves those enum values in place (safe — no rows use them).
