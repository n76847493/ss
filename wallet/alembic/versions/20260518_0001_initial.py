"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-18

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


chain_enum = sa.Enum("BTC", "ETH", "BSC", "POLYGON", "TRON", "TON", "SOL", name="chain_enum")
asset_enum = sa.Enum("BTC", "USDT", "USDC", "TON", name="asset_enum")
txtype_enum = sa.Enum(
    "DEPOSIT", "WITHDRAW", "INTERNAL_IN", "INTERNAL_OUT",
    "SWEEP", "FEE", "ADJUSTMENT",
    name="txtype_enum",
)
txstatus_enum = sa.Enum(
    "PENDING", "BROADCAST", "CONFIRMED", "FAILED", "CANCELLED",
    name="txstatus_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    chain_enum.create(bind, checkfirst=True)
    asset_enum.create(bind, checkfirst=True)
    txtype_enum.create(bind, checkfirst=True)
    txstatus_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("telegram_id", sa.BigInteger, unique=True, index=True),
        sa.Column("username", sa.String(64)),
        sa.Column("first_name", sa.String(128)),
        sa.Column("language", sa.String(8), nullable=False, server_default="ru"),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_blocked", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("totp_secret", sa.String(64)),
        sa.Column("totp_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "addresses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("chain", chain_enum, nullable=False),
        sa.Column("asset", asset_enum, nullable=False),
        sa.Column("derivation_index", sa.Integer, nullable=False),
        sa.Column("address", sa.String(128), nullable=False, index=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("chain", "address", name="uq_addresses_chain_address"),
    )
    op.create_index(
        "ix_addresses_user_chain_asset", "addresses", ["user_id", "chain", "asset"]
    )

    op.create_table(
        "balances",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("chain", chain_enum, nullable=False),
        sa.Column("asset", asset_enum, nullable=False),
        sa.Column("amount", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("locked", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "chain", "asset", name="uq_balances_user_chain_asset"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("type", txtype_enum, nullable=False),
        sa.Column("status", txstatus_enum, nullable=False, server_default="PENDING"),
        sa.Column("chain", chain_enum, nullable=False),
        sa.Column("asset", asset_enum, nullable=False),
        sa.Column("amount", sa.Numeric(38, 18), nullable=False),
        sa.Column("fee", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("usd_value", sa.Numeric(20, 4)),
        sa.Column("address_from", sa.String(128)),
        sa.Column("address_to", sa.String(128)),
        sa.Column("counterparty_user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("external_id", sa.String(128)),
        sa.Column("txid", sa.String(128), index=True),
        sa.Column("confirmations", sa.Integer, nullable=False, server_default="0"),
        sa.Column("note", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tx_user_created", "transactions", ["user_id", "created_at"])
    op.create_index("ix_tx_chain_status", "transactions", ["chain", "status"])
    op.create_index("ix_tx_external_id", "transactions", ["external_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("payload", sa.Text),
        sa.Column("ip", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_user_created", "audit_log", ["user_id", "created_at"])

    op.create_table(
        "withdrawal_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("chain", chain_enum, nullable=False),
        sa.Column("asset", asset_enum, nullable=False),
        sa.Column("amount", sa.Numeric(38, 18), nullable=False),
        sa.Column("address", sa.String(128), nullable=False),
        sa.Column("status", txstatus_enum, nullable=False, server_default="PENDING"),
        sa.Column("transaction_id", sa.Integer, sa.ForeignKey("transactions.id", ondelete="SET NULL")),
        sa.Column("twofa_verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("admin_approved", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("withdrawal_requests")
    op.drop_index("ix_audit_user_created", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_tx_external_id", table_name="transactions")
    op.drop_index("ix_tx_chain_status", table_name="transactions")
    op.drop_index("ix_tx_user_created", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("balances")
    op.drop_index("ix_addresses_user_chain_asset", table_name="addresses")
    op.drop_table("addresses")
    op.drop_table("users")
    bind = op.get_bind()
    txstatus_enum.drop(bind, checkfirst=True)
    txtype_enum.drop(bind, checkfirst=True)
    asset_enum.drop(bind, checkfirst=True)
    chain_enum.drop(bind, checkfirst=True)
