"""
Seed script for the RuleConfig table.

Source dataset: Legal Metrology Act, 2009 — Department of Consumer Affairs,
Ministry of Consumer Affairs, Food and Public Distribution, Government of India.
https://consumeraffairs.gov.in/pages/legal-metrology-act
Rules below are derived from the Legal Metrology (Packaged Commodities)
Rules, 2011, made under this Act (effective 2011-04-01).

Run against a running `db` service, from the repo root or rule-configs/,
with the backend virtualenv active:

    DATABASE_URL="postgresql+asyncpg://lmpc_user:changeme_dev_only@localhost:5432/lmpc" \
        python seed_rules.py

Idempotent: skips any field_name that already has a RuleConfig row, so it
is safe to re-run.
"""
import asyncio
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.models import RuleConfig  # noqa: E402

RULES = [
    {
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
        "field_name": "net_quantity",
        "mandatory": True,
        "regex_pattern": r"^\d+(\.\d+)?\s*(g|kg|ml|L|oz)$",
        "min_font_height_mm": 1.0,
        "placement_zone": "PDP",
        "language_requirement": None,
        "version": "1.0",
        "effective_date": date(2011, 4, 1),
    },
    {
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
        "field_name": "dimensions",
        "mandatory": False,
        "regex_pattern": None,
        "min_font_height_mm": 1.0,
        "placement_zone": None,
        "language_requirement": None,
        "version": "1.0",
        "effective_date": date(2011, 4, 1),
    },
]


async def seed_rules() -> None:
    inserted, skipped = 0, 0
    async with AsyncSessionLocal() as session:
        for rule in RULES:
            existing = await session.execute(
                select(RuleConfig).where(RuleConfig.field_name == rule["field_name"])
            )
            if existing.scalar_one_or_none() is not None:
                skipped += 1
                continue
            session.add(RuleConfig(**rule))
            inserted += 1
        await session.commit()
    print(f"seed_rules: inserted={inserted} skipped={skipped} total_rules={len(RULES)}")


if __name__ == "__main__":
    asyncio.run(seed_rules())
