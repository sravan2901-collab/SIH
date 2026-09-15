"""Integration tests for RuleConfig seeding and schema verification.

Verifies that alembic migrations seed all 9 LMPC RuleConfig rows --
the 7 original Phase 0 rows plus 2 added by the schema-hardening migration
(generic_name, country_of_origin) -- per the LMPC Problem Statement ID 26034
and Legal Metrology (Packaged Commodities) Rules, 2011.
Source: https://consumeraffairs.gov.in/pages/legal-metrology-act
"""
import asyncio
from datetime import date

import asyncpg
import pytest

from app.database import DATABASE_URL

pytestmark = pytest.mark.integration


def test_rule_configs_has_exactly_nine_rows_and_correct_rules():
    """Assert rule_configs has exactly 9 rows after alembic upgrade head.

    Original 7 rows (Phase 0): MRP, net_quantity, mfg_date, manufacturer_address,
      consumer_care, unit_sale_price, dimensions.
    Added by schema-hardening migration (PS gap): generic_name, country_of_origin.
    All mandatory fields and regex patterns match LMPC Rules 2011.
    """
    async def _query():
        conn = await asyncpg.connect(dsn=DATABASE_URL.replace("+asyncpg", ""))
        try:
            return await conn.fetch("SELECT * FROM rule_configs")
        finally:
            await conn.close()

    rows = asyncio.run(_query())
    assert len(rows) == 9, f"Expected exactly 9 rule_configs rows, got {len(rows)}"

    rules_by_field = {row["field_name"]: dict(row) for row in rows}

    expected_fields = {
        "MRP",
        "net_quantity",
        "mfg_date",
        "manufacturer_address",
        "consumer_care",
        "unit_sale_price",
        "dimensions",
        "generic_name",
        "country_of_origin",
    }
    assert set(rules_by_field.keys()) == expected_fields

    # MRP row: mandatory=True, listed regex_pattern, 1.0mm min font height, PDP zone
    mrp = rules_by_field["MRP"]
    assert mrp["mandatory"] is True
    assert mrp["regex_pattern"] == r"^(₹|Rs\.?)\s*\d+(\.\d{1,2})?$"
    assert mrp["min_font_height_mm"] == 1.0
    assert mrp["placement_zone"] == "PDP"
    assert mrp["language_requirement"] is None
    assert mrp["version"] == "1.0"
    assert mrp["effective_date"] == date(2011, 4, 1)

    # net_quantity row: mandatory=True, 2.0mm min font height, PDP zone
    net_qty = rules_by_field["net_quantity"]
    assert net_qty["mandatory"] is True
    assert net_qty["regex_pattern"] == r"^\d+(\.\d+)?\s*(g|kg|ml|L|oz)$"
    assert net_qty["min_font_height_mm"] == 2.0
    assert net_qty["placement_zone"] == "PDP"
    assert net_qty["language_requirement"] is None
    assert net_qty["version"] == "1.0"
    assert net_qty["effective_date"] == date(2011, 4, 1)

    # mfg_date row: mandatory=True, MM/YYYY regex pattern
    mfg_date = rules_by_field["mfg_date"]
    assert mfg_date["mandatory"] is True
    assert mfg_date["regex_pattern"] == r"^(0[1-9]|1[0-2])/\d{4}$"
    assert mfg_date["min_font_height_mm"] == 1.0
    assert mfg_date["placement_zone"] is None

    # manufacturer_address row: mandatory=True, no regex
    mfg_addr = rules_by_field["manufacturer_address"]
    assert mfg_addr["mandatory"] is True
    assert mfg_addr["regex_pattern"] is None
    assert mfg_addr["min_font_height_mm"] == 1.0

    # consumer_care row: mandatory=True, no regex
    care = rules_by_field["consumer_care"]
    assert care["mandatory"] is True
    assert care["regex_pattern"] is None
    assert care["min_font_height_mm"] == 1.0

    # unit_sale_price row: mandatory=False, same regex as MRP, PDP zone
    usp = rules_by_field["unit_sale_price"]
    assert usp["mandatory"] is False
    assert usp["regex_pattern"] == r"^(₹|Rs\.?)\s*\d+(\.\d{1,2})?$"
    assert usp["min_font_height_mm"] == 1.0
    assert usp["placement_zone"] == "PDP"

    # dimensions row: mandatory=False, no regex
    dim = rules_by_field["dimensions"]
    assert dim["mandatory"] is False
    assert dim["regex_pattern"] is None
    assert dim["min_font_height_mm"] == 1.0

    # generic_name: mandatory=True, no regex, PDP zone (LMPC Rules 2011 Rule 6(1)(a))
    gn = rules_by_field["generic_name"]
    assert gn["mandatory"] is True
    assert gn["regex_pattern"] is None
    assert gn["min_font_height_mm"] == 1.0
    assert gn["placement_zone"] == "PDP"
    assert gn["effective_date"] == date(2011, 4, 1)

    # country_of_origin: mandatory=True, no regex (LMPC Rules 2011 Rule 6(1)(k))
    coo = rules_by_field["country_of_origin"]
    assert coo["mandatory"] is True
    assert coo["regex_pattern"] is None
    assert coo["min_font_height_mm"] == 1.0
    assert coo["effective_date"] == date(2011, 4, 1)
