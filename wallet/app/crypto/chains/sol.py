"""Solana adapter (USDC SPL token)."""
from __future__ import annotations

from decimal import Decimal

import httpx

from ...config import get_settings
from ...db.models import Asset, Chain
from ..hd import derive_solana
from .base import OfflineError, OnChainTx


class SolanaAdapter:
    chain = Chain.SOL

    def __init__(self) -> None:
        s = get_settings()
        self._rpc = (s.sol_rpc_url or "https://api.mainnet-beta.solana.com").rstrip("/")
        self._usdc_mint = s.sol_usdc_mint
        self._client = httpx.AsyncClient(timeout=20.0)

    def derive_address(self, index: int) -> str:
        return derive_solana(index).address

    async def _rpc_call(self, method: str, params: list) -> dict:
        r = await self._client.post(
            self._rpc,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        )
        r.raise_for_status()
        return r.json()

    async def balance_of(self, address: str, asset: Asset) -> Decimal:
        if asset != Asset.USDC:
            return Decimal(0)
        d = await self._rpc_call(
            "getTokenAccountsByOwner",
            [address, {"mint": self._usdc_mint}, {"encoding": "jsonParsed"}],
        )
        total = Decimal(0)
        for acc in d.get("result", {}).get("value", []):
            ui = acc["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmountString"]
            total += Decimal(ui)
        return total

    async def incoming_since(
        self, address: str, asset: Asset, since_height: int = 0
    ) -> list[OnChainTx]:
        if asset != Asset.USDC:
            return []
        # Get owner token accounts, then for each list signatures and parse.
        d = await self._rpc_call(
            "getTokenAccountsByOwner",
            [address, {"mint": self._usdc_mint}, {"encoding": "jsonParsed"}],
        )
        out: list[OnChainTx] = []
        for acc in d.get("result", {}).get("value", []):
            token_account = acc["pubkey"]
            sigs = await self._rpc_call("getSignaturesForAddress", [token_account, {"limit": 25}])
            for s in sigs.get("result", []):
                out.append(
                    OnChainTx(
                        txid=s["signature"],
                        asset=Asset.USDC,
                        address=address,
                        counterparty=None,
                        amount=Decimal(0),  # would parse tx for precise delta
                        confirmations=1 if s.get("confirmationStatus") == "finalized" else 0,
                        block_height=s.get("slot"),
                    )
                )
        return out

    async def send(self, *, from_index: int, to_address: str, asset: Asset, amount: Decimal) -> str:
        raise OfflineError(
            "Solana withdrawal requires solders signing — implement against your custody policy."
        )
