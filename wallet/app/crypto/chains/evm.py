"""EVM adapter (Ethereum / BSC / Polygon).

Native asset is the gas token for that chain (ETH, BNB, MATIC). For our
purposes we currently only credit the ERC-20/BEP-20 token balances of
USDT and USDC, since the bot's supported assets are BTC / USDT / USDC /
TON. The adapter is structured so adding native crediting is a one-liner
(set ``native_asset`` in the constructor).
"""
from __future__ import annotations

from decimal import Decimal

from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware

from ...db.models import Asset, Chain
from ..hd import derive_evm
from .base import OfflineError, OnChainTx, TokenSpec

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    },
]


class EVMAdapter:
    def __init__(
        self,
        *,
        chain: Chain,
        rpc_url: str,
        tokens: dict[Asset, TokenSpec],
        native_asset: Asset | None = None,
    ) -> None:
        self.chain = chain
        self._tokens = tokens
        self._native_asset = native_asset
        self._w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        if chain in (Chain.BSC, Chain.POLYGON):
            self._w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    def derive_address(self, index: int) -> str:
        return derive_evm(index).address

    async def balance_of(self, address: str, asset: Asset) -> Decimal:
        if asset == self._native_asset:
            wei = await self._w3.eth.get_balance(self._w3.to_checksum_address(address))
            return Decimal(wei) / Decimal(10**18)
        spec = self._tokens.get(asset)
        if spec is None:
            return Decimal(0)
        contract = self._w3.eth.contract(
            address=self._w3.to_checksum_address(spec.contract), abi=ERC20_ABI
        )
        raw = await contract.functions.balanceOf(self._w3.to_checksum_address(address)).call()
        return Decimal(raw) / Decimal(10**spec.decimals)

    async def incoming_since(
        self, address: str, asset: Asset, since_height: int = 0
    ) -> list[OnChainTx]:
        spec = self._tokens.get(asset)
        if spec is None:
            return []
        self._w3.eth.contract(
            address=self._w3.to_checksum_address(spec.contract), abi=ERC20_ABI
        )
        tip = await self._w3.eth.block_number
        from_block = max(since_height, tip - 5000)  # chunk scan range
        topic_to = "0x" + self._w3.to_checksum_address(address)[2:].lower().rjust(64, "0")
        logs = await self._w3.eth.get_logs(
            {
                "fromBlock": from_block,
                "toBlock": tip,
                "address": self._w3.to_checksum_address(spec.contract),
                "topics": [
                    self._w3.keccak(text="Transfer(address,address,uint256)").hex(),
                    None,
                    topic_to,
                ],
            }
        )
        out: list[OnChainTx] = []
        for lg in logs:
            value = int(lg["data"], 16) if isinstance(lg["data"], str) else int.from_bytes(lg["data"], "big")
            sender = "0x" + lg["topics"][1].hex()[-40:]
            out.append(
                OnChainTx(
                    txid=lg["transactionHash"].hex(),
                    asset=asset,
                    address=address,
                    counterparty=self._w3.to_checksum_address(sender),
                    amount=Decimal(value) / Decimal(10**spec.decimals),
                    confirmations=max(0, tip - lg["blockNumber"] + 1),
                    block_height=lg["blockNumber"],
                )
            )
        return out

    async def send(self, *, from_index: int, to_address: str, asset: Asset, amount: Decimal) -> str:
        spec = self._tokens.get(asset)
        if spec is None:
            raise OfflineError(f"{asset} not supported on {self.chain}")
        from ..hd import derive_evm as _derive

        key = _derive(from_index)
        acct = self._w3.eth.account.from_key("0x" + key.private_key_hex)
        contract = self._w3.eth.contract(
            address=self._w3.to_checksum_address(spec.contract), abi=ERC20_ABI
        )
        nonce = await self._w3.eth.get_transaction_count(acct.address)
        gas_price = await self._w3.eth.gas_price
        amt = int(amount * (Decimal(10) ** spec.decimals))
        tx = await contract.functions.transfer(self._w3.to_checksum_address(to_address), amt).build_transaction(
            {
                "from": acct.address,
                "nonce": nonce,
                "gasPrice": gas_price,
                "gas": 80000,
            }
        )
        signed = acct.sign_transaction(tx)
        txh = await self._w3.eth.send_raw_transaction(signed.rawTransaction)
        return txh.hex()
