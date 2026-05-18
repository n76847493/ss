"""Chain-specific adapters.

Adapters are exposed via :func:`get_adapter` and follow the protocol in
``base.py``. Each adapter is responsible for:

* generating a deposit address from a derivation index
* querying the on-chain balance of an address
* listing incoming transfers since a given height/timestamp
* broadcasting a withdrawal transaction signed with the operator key

Online behaviour is gated by RPC configuration — if RPC creds are missing,
``get_adapter`` returns an :class:`OfflineAdapter` for that chain which
still derives addresses but raises :class:`OfflineError` for network ops.
"""
from __future__ import annotations

from ...config import get_settings
from ...db.models import Asset, Chain
from .base import ChainAdapter, OfflineAdapter, OfflineError, OnChainTx, TokenSpec
from .btc import BitcoinAdapter
from .evm import EVMAdapter
from .sol import SolanaAdapter
from .ton import TONAdapter
from .tron import TronAdapter

__all__ = [
    "ChainAdapter",
    "OfflineAdapter",
    "OfflineError",
    "OnChainTx",
    "TokenSpec",
    "get_adapter",
]


def get_adapter(chain: Chain) -> ChainAdapter:
    s = get_settings()
    if chain == Chain.BTC:
        if s.btc_rpc_url or s.btc_esplora_url:
            return BitcoinAdapter()
        return OfflineAdapter(chain)
    if chain == Chain.ETH:
        if s.eth_rpc_url:
            return EVMAdapter(
                chain=Chain.ETH,
                rpc_url=s.eth_rpc_url,
                tokens={
                    Asset.USDT: TokenSpec(symbol="USDT", contract=s.eth_usdt_contract, decimals=6),
                    Asset.USDC: TokenSpec(symbol="USDC", contract=s.eth_usdc_contract, decimals=6),
                },
                native_asset=None,
            )
        return OfflineAdapter(chain)
    if chain == Chain.BSC:
        if s.bsc_rpc_url:
            return EVMAdapter(
                chain=Chain.BSC,
                rpc_url=s.bsc_rpc_url,
                tokens={
                    Asset.USDT: TokenSpec(symbol="USDT", contract=s.bsc_usdt_contract, decimals=18),
                    Asset.USDC: TokenSpec(symbol="USDC", contract=s.bsc_usdc_contract, decimals=18),
                },
                native_asset=None,
            )
        return OfflineAdapter(chain)
    if chain == Chain.POLYGON:
        if s.polygon_rpc_url:
            return EVMAdapter(
                chain=Chain.POLYGON,
                rpc_url=s.polygon_rpc_url,
                tokens={
                    Asset.USDT: TokenSpec(symbol="USDT", contract=s.polygon_usdt_contract, decimals=6),
                    Asset.USDC: TokenSpec(symbol="USDC", contract=s.polygon_usdc_contract, decimals=6),
                },
                native_asset=None,
            )
        return OfflineAdapter(chain)
    if chain == Chain.TRON:
        return TronAdapter()
    if chain == Chain.TON:
        return TONAdapter()
    if chain == Chain.SOL:
        return SolanaAdapter()
    raise ValueError(f"unsupported chain {chain}")
