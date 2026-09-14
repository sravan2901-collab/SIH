"""seed_rule_configs

Source dataset: Legal Metrology Act, 2009 — Department of Consumer Affairs,
Ministry of Consumer Affairs, Food and Public Distribution, Government of India.
https://consumeraffairs.gov.in/pages/legal-metrology-act
Rules below are derived from the Legal Metrology (Packaged Commodities)
Rules, 2011, made under this Act (effective 2011-04-01).

Revision ID: d95af3386181
Revises: 164db70a116d
Create Date: 2026-09-14 10:20:40.473219

"""
from datetime import date
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd95af3386181'
down_revision: Union[str, None] = '164db70a116d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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

    # Clean existing rows if any to ensure clean, idempotent seed with exact specifications
    op.execute(
        "DELETE FROM rule_configs WHERE field_name IN ("
        "'MRP', 'net_quantity', 'mfg_date', 'manufacturer_address', "
        "'consumer_care', 'unit_sale_price', 'dimensions')"
    )

    op.bulk_insert(
        rule_configs_table,
        [
            {
                "rule_id": uuid4(),
                "field_name": "MRP",
                "mandatory": True,
                "regex_pattern": r"^(₹|Rs\.?)\s*\d+(\.\d{1,2})?$",
                "min_font_height_mm": 1.0,
                "placement_zone": "PDP",
                "language_requirement": None,
                "version": "1.0",
                "effective_date": date(2011, 4, 1),
            },
            {
                "rule_id": uuid4(),
                "field_name": "net_quantity",
                "mandatory": True,
                "regex_pattern": r"^\d+(\.\d+)?\s*(g|kg|ml|L|oz)$",
                "min_font_height_mm": 2.0,
                "placement_zone": "PDP",
                "language_requirement": None,
                "version": "1.0",
                "effective_date": date(2011, 4, 1),
            },
            {
                "rule_id": uuid4(),
                "field_name": "mfg_date",
                "mandatory": True,
                "regex_pattern": r"^(0[1-9]|1[0-2])/\d{4}$",
                "min_font_height_mm": 1.0,
                "placement_zone": None,
                "language_requirement": None,
                "version": "1.0",
                "effective_date": date(2011, 4, 1),
            },
            {
                "rule_id": uuid4(),
                "field_name": "manufacturer_address",
                "mandatory": True,
                "regex_pattern": None,
                "min_font_height_mm": 1.0,
                "placement_zone": None,
                "language_requirement": None,
                "version": "1.0",
                "effective_date": date(2011, 4, 1),
            },
            {
                "rule_id": uuid4(),
                "field_name": "consumer_care",
                "mandatory": True,
                "regex_pattern": None,
                "min_font_height_mm": 1.0,
                "placement_zone": None,
                "language_requirement": None,
                "version": "1.0",
                "effective_date": date(2011, 4, 1),
            },
            {
                "rule_id": uuid4(),
                "field_name": "unit_sale_price",
                "mandatory": False,
                "regex_pattern": r"^(₹|Rs\.?)\s*\d+(\.\d{1,2})?$",
                "min_font_height_mm": 1.0,
                "placement_zone": "PDP",
                "language_requirement": None,
                "version": "1.0",
                "effective_date": date(2011, 4, 1),
            },
            {
                "rule_id": uuid4(),
                "field_name": "dimensions",
                "mandatory": False,
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
    op.execute(
        "DELETE FROM rule_configs WHERE field_name IN ("
        "'MRP', 'net_quantity', 'mfg_date', 'manufacturer_address', "
        "'consumer_care', 'unit_sale_price', 'dimensions')"
    )

