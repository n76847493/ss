"""Asset/chain registry.

Defines which (chain, asset) pairs are supported and exposes helpers for
display names and BIP44 derivation. Edit this file to add or remove a
network.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..db.models import Asset, Chain


@dataclass(frozen=True)
class Network:
    chain: Chain
    asset: Asset
    label: str
    explorer_address: str
    explorer_tx: str
    min_confirmations: int


NETWORKS: list[Network] = [
    Network(Chain.BTC, Asset.BTC, "Bitcoin", "https://blockstream.info/address/{a}",
            "https://blockstream.info/tx/{a}", 2),

    Network(Chain.ETH, Asset.USDT, "USDT (ERC-20, Ethereum)",
            "https://etherscan.io/address/{a}", "https://etherscan.io/tx/{a}", 12),
    Network(Chain.ETH, Asset.USDC, "USDC (ERC-20, Ethereum)",
            "https://etherscan.io/address/{a}", "https://etherscan.io/tx/{a}", 12),

    Network(Chain.BSC, Asset.USDT, "USDT (BEP-20, BSC)",
            "https://bscscan.com/address/{a}", "https://bscscan.com/tx/{a}", 15),
    Network(Chain.BSC, Asset.USDC, "USDC (BEP-20, BSC)",
            "https://bscscan.com/address/{a}", "https://bscscan.com/tx/{a}", 15),

    Network(Chain.POLYGON, Asset.USDT, "USDT (Polygon)",
            "https://polygonscan.com/address/{a}", "https://polygonscan.com/tx/{a}", 30),
    Network(Chain.POLYGON, Asset.USDC, "USDC (Polygon)",
            "https://polygonscan.com/address/{a}", "https://polygonscan.com/tx/{a}", 30),

    Network(Chain.TRON, Asset.USDT, "USDT (TRC-20, Tron)",
            "https://tronscan.org/#/address/{a}", "https://tronscan.org/#/transaction/{a}", 19),
    Network(Chain.TRON, Asset.USDC, "USDC (TRC-20, Tron)",
            "https://tronscan.org/#/address/{a}", "https://tronscan.org/#/transaction/{a}", 19),

    Network(Chain.TON, Asset.TON, "TON",
            "https://tonscan.org/address/{a}", "https://tonscan.org/tx/{a}", 1),
    Network(Chain.TON, Asset.USDT, "USDT (Jetton, TON)",
            "https://tonscan.org/address/{a}", "https://tonscan.org/tx/{a}", 1),

    Network(Chain.SOL, Asset.USDC, "USDC (SPL, Solana)",
            "https://solscan.io/account/{a}", "https://solscan.io/tx/{a}", 32),
]


def list_networks_for_asset(asset: Asset) -> list[Network]:
    return [n for n in NETWORKS if n.asset == asset]


def get_network(chain: Chain, asset: Asset) -> Network | None:
    for n in NETWORKS:
        if n.chain == chain and n.asset == asset:
            return n
    return None


SUPPORTED_ASSETS: list[Asset] = [Asset.BTC, Asset.USDT, Asset.USDC, Asset.TON]
