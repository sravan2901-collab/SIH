"""seed_admin_user

Revision ID: 164db70a116d
Revises: 716f2ca1b437
Create Date: 2026-09-09 09:03:46.671475

"""
from datetime import datetime
from typing import Sequence, Union
from uuid import uuid4

import bcrypt
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '164db70a116d'
down_revision: Union[str, None] = '716f2ca1b437'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOTE: dev-only seed credential. Rotate before any non-local deployment.
    # Plaintext exists only here, at migration-write time, to compute the
    # bcrypt hash stored below — the plaintext itself is never stored.
    DEV_ADMIN_PASSWORD = "ChangeMe_Dev_Only!123"
    password_hash = bcrypt.hashpw(
        DEV_ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    users_table = sa.table(
        "users",
        sa.column("user_id", sa.UUID()),
        sa.column("name", sa.String()),
        sa.column("email", sa.String()),
        sa.column("password_hash", sa.String()),
        sa.column(
            "role",
            sa.Enum("Inspector", "Reviewer", "Admin", name="role_enum", create_type=False),
        ),
        sa.column("region", sa.String()),
        sa.column("created_at", sa.DateTime()),
    )

    op.bulk_insert(
        users_table,
        [
            {
                "user_id": uuid4(),
                "name": "Admin",
                "email": "admin@lmpc.gov",
                "password_hash": password_hash,
                "role": "Admin",
                "region": "National",
                "created_at": datetime.utcnow(),
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE email = 'admin@lmpc.gov'")
