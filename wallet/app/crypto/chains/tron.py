"""TRON adapter (USDT-TRC20, USDC-TRC20)."""
from __future__ import annotations

from decimal import Decimal

import httpx

from ...config import get_settings
from ...db.models import Asset, Chain
from ..hd import derive_tron
from .base import OnChainTx

TRX_DEC = Decimal(10**6)


def _hex_to_base58(hex_addr: str) -> str:
    """Convert TRON hex address (0x41...) to base58check."""
    import hashlib

    import base58

    if hex_addr.startswith("0x"):
        hex_addr = hex_addr[2:]
    if len(hex_addr) == 40:  # missing 0x41 prefix
        hex_addr = "41" + hex_addr
    raw = bytes.fromhex(hex_addr)
    check = hashlib.sha256(hashlib.sha256(raw).digest()).digest()[:4]
    return base58.b58encode(raw + check).decode()


class TronAdapter:
    chain = Chain.TRON

    def __init__(self) -> None:
        s = get_settings()
        self._api = (s.tron_api_url or "https://api.trongrid.io").rstrip("/")
        self._key = s.tron_api_key
        self._tokens = {
            Asset.USDT: (s.tron_usdt_contract, 6),
            Asset.USDC: (s.tron_usdc_contract, 6),
        }
        self._client = httpx.AsyncClient(
            timeout=20.0,
            headers={"TRON-PRO-API-KEY": self._key} if self._key else {},
        )

    def derive_address(self, index: int) -> str:
        return derive_tron(index).address

    async def balance_of(self, address: str, asset: Asset) -> Decimal:
        if asset not in self._tokens:
            return Decimal(0)
        contract, dec = self._tokens[asset]
        r = await self._client.post(
            f"{self._api}/wallet/triggerconstantcontract",
            json={
                "owner_address": address,
                "contract_address": contract,
                "function_selector": "balanceOf(address)",
                "parameter": address_to_hex_arg(address),
                "visible": True,
            },
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("constant_result") or [""]
        raw = int(results[0] or "0", 16)
        return Decimal(raw) / Decimal(10**dec)

    async def incoming_since(
        self, address: str, asset: Asset, since_height: int = 0
    ) -> list[OnChainTx]:
        if asset not in self._tokens:
            return []
        contract, dec = self._tokens[asset]
        r = await self._client.get(
            f"{self._api}/v1/accounts/{address}/transactions/trc20",
            params={"contract_address": contract, "limit": 50, "only_to": "true"},
        )
        r.raise_for_status()
        out: list[OnChainTx] = []
        for tx in r.json().get("data", []):
            block = tx.get("block_timestamp")
            out.append(
                OnChainTx(
                    txid=tx["transaction_id"],
                    asset=asset,
                    address=address,
                    counterparty=tx.get("from"),
                    amount=Decimal(tx.get("value", "0")) / Decimal(10**dec),
                    confirmations=1 if tx.get("confirmed") else 0,
                    block_height=block,
                )
            )
        return out

    async def send(self, *, from_index: int, to_address: str, asset: Asset, amount: Decimal) -> str:
        # Live broadcast uses tronpy.AsyncTron; gated behind import so the
        # bot still imports cleanly when tronpy is missing.
        from tronpy import AsyncTron  # type: ignore
        from tronpy.keys import PrivateKey  # type: ignore
        from tronpy.providers import AsyncHTTPProvider  # type: ignore

        if asset not in self._tokens:
            raise ValueError(f"{asset} not supported on TRON")
        contract_addr, dec = self._tokens[asset]
        key = derive_tron(from_index)
        priv = PrivateKey(bytes.fromhex(key.private_key_hex))
        client = AsyncTron(provider=AsyncHTTPProvider(self._api, api_key=self._key or None))
        try:
            contract = await client.get_contract(contract_addr)
            txn = await (
                contract.functions.transfer(to_address, int(amount * Decimal(10**dec)))
                .with_owner(key.address)
                .fee_limit(40_000_000)
                .build()
            )
            signed = txn.sign(priv)
            res = await signed.broadcast()
            return res.get("txid") or res.get("transaction", {}).get("txID", "")
        finally:
            await client.close()


def address_to_hex_arg(address: str) -> str:
    """Encode a base58check TRON address as the 64-char hex arg expected by tron API."""
    import base58

    raw = base58.b58decode_check(address)
    # raw[0] == 0x41; we want the 20-byte body padded to 32 bytes
    return raw[1:].hex().rjust(64, "0")
