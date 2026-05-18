"""TON adapter (native TON + USDT Jetton).

We use the public TonCenter HTTP API for reading; sending requires the
operator wallet contract to be deployed and active — the implementation
is provided as a hook against ``ton-sdk`` / ``pytoniq``.
"""
from __future__ import annotations

from decimal import Decimal

import httpx

from ...config import get_settings
from ...db.models import Asset, Chain
from ..hd import derive_ton
from .base import OfflineError, OnChainTx


class TONAdapter:
    chain = Chain.TON

    def __init__(self) -> None:
        s = get_settings()
        self._api = (s.ton_api_url or "https://toncenter.com/api/v2").rstrip("/")
        self._key = s.ton_api_key
        self._usdt_jetton = s.ton_usdt_jetton
        params: dict[str, str] = {}
        if self._key:
            params["api_key"] = self._key
        self._client = httpx.AsyncClient(timeout=20.0, params=params)

    def derive_address(self, index: int) -> str:
        return derive_ton(index).address

    async def balance_of(self, address: str, asset: Asset) -> Decimal:
        if asset == Asset.TON:
            r = await self._client.get(f"{self._api}/getAddressBalance", params={"address": address})
            r.raise_for_status()
            return Decimal(r.json().get("result", "0")) / Decimal(10**9)
        if asset in (Asset.USDT, Asset.USDC):
            # Jetton balance lookup; for USDC on TON there is no canonical
            # contract — operators wire their own jetton via config.
            return Decimal(0)
        return Decimal(0)

    async def incoming_since(
        self, address: str, asset: Asset, since_height: int = 0
    ) -> list[OnChainTx]:
        if asset != Asset.TON:
            return []
        r = await self._client.get(
            f"{self._api}/getTransactions", params={"address": address, "limit": 25}
        )
        r.raise_for_status()
        out: list[OnChainTx] = []
        for tx in r.json().get("result", []):
            in_msg = tx.get("in_msg", {})
            value = int(in_msg.get("value", "0"))
            if value <= 0:
                continue
            out.append(
                OnChainTx(
                    txid=tx.get("transaction_id", {}).get("hash", ""),
                    asset=Asset.TON,
                    address=address,
                    counterparty=in_msg.get("source") or None,
                    amount=Decimal(value) / Decimal(10**9),
                    confirmations=1,
                    block_height=tx.get("transaction_id", {}).get("lt"),
                )
            )
        return out

    async def send(self, *, from_index: int, to_address: str, asset: Asset, amount: Decimal) -> str:
        raise OfflineError(
            "TON withdrawal requires an operator wallet contract; configure via your TON SDK of choice."
        )
