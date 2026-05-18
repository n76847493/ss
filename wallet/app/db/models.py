"""ORM models for the custodial wallet."""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Chain(enum.StrEnum):
    BTC = "BTC"
    ETH = "ETH"
    BSC = "BSC"
    POLYGON = "POLYGON"
    TRON = "TRON"
    TON = "TON"
    SOL = "SOL"


class Asset(enum.StrEnum):
    BTC = "BTC"
    USDT = "USDT"
    USDC = "USDC"
    TON = "TON"


class TxType(enum.StrEnum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    INTERNAL_IN = "INTERNAL_IN"
    INTERNAL_OUT = "INTERNAL_OUT"
    SWEEP = "SWEEP"
    FEE = "FEE"
    ADJUSTMENT = "ADJUSTMENT"


class TxStatus(enum.StrEnum):
    PENDING = "PENDING"
    BROADCAST = "BROADCAST"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="ru")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    addresses: Mapped[list[Address]] = relationship(back_populates="user", cascade="all, delete-orphan")
    balances: Mapped[list[Balance]] = relationship(back_populates="user", cascade="all, delete-orphan")
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Transaction.user_id",
    )


class Address(Base):
    """A deposit address derived from the operator HD seed for one user/asset/chain."""

    __tablename__ = "addresses"
    __table_args__ = (
        UniqueConstraint("chain", "address", name="uq_addresses_chain_address"),
        Index("ix_addresses_user_chain_asset", "user_id", "chain", "asset"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    chain: Mapped[Chain] = mapped_column(Enum(Chain, name="chain_enum"))
    asset: Mapped[Asset] = mapped_column(Enum(Asset, name="asset_enum"))
    derivation_index: Mapped[int] = mapped_column(Integer)
    address: Mapped[str] = mapped_column(String(128), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="addresses")


class Balance(Base):
    """Internal off-chain balance — the source of truth for what the user owns."""

    __tablename__ = "balances"
    __table_args__ = (
        UniqueConstraint("user_id", "chain", "asset", name="uq_balances_user_chain_asset"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    chain: Mapped[Chain] = mapped_column(Enum(Chain, name="chain_enum"))
    asset: Mapped[Asset] = mapped_column(Enum(Asset, name="asset_enum"))
    amount: Mapped[Decimal] = mapped_column(Numeric(38, 18), default=Decimal("0"))
    locked: Mapped[Decimal] = mapped_column(Numeric(38, 18), default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="balances")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_tx_user_created", "user_id", "created_at"),
        Index("ix_tx_chain_status", "chain", "status"),
        Index("ix_tx_external_id", "external_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[TxType] = mapped_column(Enum(TxType, name="txtype_enum"))
    status: Mapped[TxStatus] = mapped_column(Enum(TxStatus, name="txstatus_enum"), default=TxStatus.PENDING)
    chain: Mapped[Chain] = mapped_column(Enum(Chain, name="chain_enum"))
    asset: Mapped[Asset] = mapped_column(Enum(Asset, name="asset_enum"))
    amount: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    fee: Mapped[Decimal] = mapped_column(Numeric(38, 18), default=Decimal("0"))
    usd_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    address_from: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address_to: Mapped[str | None] = mapped_column(String(128), nullable=True)
    counterparty_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    txid: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    confirmations: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(
        back_populates="transactions", foreign_keys=[user_id]
    )


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event: Mapped[str] = mapped_column(String(64))
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    chain: Mapped[Chain] = mapped_column(Enum(Chain, name="chain_enum"))
    asset: Mapped[Asset] = mapped_column(Enum(Asset, name="asset_enum"))
    amount: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    address: Mapped[str] = mapped_column(String(128))
    status: Mapped[TxStatus] = mapped_column(Enum(TxStatus, name="txstatus_enum"), default=TxStatus.PENDING)
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    twofa_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    admin_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
