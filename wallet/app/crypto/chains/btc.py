"""Bitcoin adapter backed by an Esplora-compatible HTTP API.

This implementation talks to a public Esplora-like service (default:
``https://blockstream.info/api``) for read paths (balance, list incoming
transfers). Withdrawals require a Bitcoin Core RPC URL — without it, sends
raise :class:`OfflineError`.
"""
from __future__ import annotations

from decimal import Decimal

import httpx

from ...config import get_settings
from ...db.models import Asset, Chain
from ..hd import derive_btc
from .base import OfflineError, OnChainTx

SATOSHI = Decimal("100000000")


class BitcoinAdapter:
    chain = Chain.BTC

    def __init__(self) -> None:
        s = get_settings()
        self._esplora = (s.btc_esplora_url or "https://blockstream.info/api").rstrip("/")
        self._rpc = s.btc_rpc_url
        self._client = httpx.AsyncClient(timeout=20.0)

    def derive_address(self, index: int) -> str:
        return derive_btc(index).address

    async def balance_of(self, address: str, asset: Asset = Asset.BTC) -> Decimal:
        if asset != Asset.BTC:
            return Decimal(0)
        r = await self._client.get(f"{self._esplora}/address/{address}")
        r.raise_for_status()
        d = r.json()
        funded = d["chain_stats"]["funded_txo_sum"]
        spent = d["chain_stats"]["spent_txo_sum"]
        return (Decimal(funded) - Decimal(spent)) / SATOSHI

    async def incoming_since(
        self, address: str, asset: Asset = Asset.BTC, since_height: int = 0
    ) -> list[OnChainTx]:
        if asset != Asset.BTC:
            return []
        r = await self._client.get(f"{self._esplora}/address/{address}/txs")
        r.raise_for_status()
        out: list[OnChainTx] = []
        tip_r = await self._client.get(f"{self._esplora}/blocks/tip/height")
        tip_r.raise_for_status()
        tip = int(tip_r.text)
        for tx in r.json():
            block = tx.get("status", {}).get("block_height")
            if block is None or block < since_height:
                continue
            value = sum(
                int(o["value"]) for o in tx.get("vout", []) if o.get("scriptpubkey_address") == address
            )
            if value == 0:
                continue
            confirmations = max(0, tip - block + 1)
            out.append(
                OnChainTx(
                    txid=tx["txid"],
                    asset=Asset.BTC,
                    address=address,
                    counterparty=None,
                    amount=Decimal(value) / SATOSHI,
                    confirmations=confirmations,
                    block_height=block,
                )
            )
        return out

    async def send(self, *, from_index: int, to_address: str, asset: Asset, amount: Decimal) -> str:
        # Withdrawals from the hot wallet require a signed-Bitcoin-Core RPC
        # path; we deliberately leave the network broadcast to the operator's
        # Bitcoin Core node to avoid embedding a brittle in-house signer in
        # the bot. Connect bitcoind via BTC_RPC_URL.
        if not self._rpc:
            raise OfflineError(
                "BTC withdrawals require BTC_RPC_URL pointing at a Bitcoin Core RPC endpoint"
            )
        # Build raw tx using the derived key with python-bitcoinlib or use
        # `sendtoaddress` against the node's hot wallet. Implementation is
        # left as an operator-configurable hook; we document the contract
        # rather than ship an untested signer.
        raise NotImplementedError(
            "Configure Bitcoin Core RPC and implement send() against your wallet policy."
        )
