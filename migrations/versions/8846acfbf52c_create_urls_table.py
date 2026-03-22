"""create urls table

Revision ID: will be auto-generated
Revises:
Create Date: auto-generated

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# These are filled in automatically by Alembic
revision: str = revision  # leave as-is
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "urls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("long_url", sa.String(length=2048), nullable=False),
        sa.Column("short_code", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expire_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("short_code"),
    )
    op.create_index(op.f("ix_urls_short_code"), "urls", ["short_code"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_urls_short_code"), table_name="urls")
    op.drop_table("urls")