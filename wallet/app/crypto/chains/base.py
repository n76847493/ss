"""Chain-adapter protocol shared by all networks."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from ...db.models import Asset, Chain


class OfflineError(RuntimeError):
    """Raised when an online operation is attempted while RPC is unconfigured."""


@dataclass(frozen=True)
class TokenSpec:
    symbol: str
    contract: str
    decimals: int


@dataclass(frozen=True)
class OnChainTx:
    txid: str
    asset: Asset
    address: str  # the receiving address that belongs to us
    counterparty: str | None
    amount: Decimal
    confirmations: int
    block_height: int | None


class ChainAdapter(Protocol):
    chain: Chain

    def derive_address(self, index: int) -> str: ...

    async def balance_of(self, address: str, asset: Asset) -> Decimal: ...

    async def incoming_since(self, address: str, asset: Asset, since_height: int = 0) -> list[OnChainTx]: ...

    async def send(self, *, from_index: int, to_address: str, asset: Asset, amount: Decimal) -> str:
        """Sign with the derived key for ``from_index`` and broadcast. Returns txid."""


class OfflineAdapter:
    """Adapter that still derives addresses but rejects all network operations."""

    def __init__(self, chain: Chain) -> None:
        self.chain = chain

    def derive_address(self, index: int) -> str:
        from ..hd import derive

        return derive(self.chain, index).address

    async def balance_of(self, address: str, asset: Asset) -> Decimal:
        raise OfflineError(f"RPC for {self.chain} not configured")

    async def incoming_since(self, address: str, asset: Asset, since_height: int = 0) -> list[OnChainTx]:
        raise OfflineError(f"RPC for {self.chain} not configured")

    async def send(self, *, from_index: int, to_address: str, asset: Asset, amount: Decimal) -> str:
        raise OfflineError(f"RPC for {self.chain} not configured")
