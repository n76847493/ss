"""HD wallet address derivation for all supported chains.

Derivation paths (BIP44 / chain-specific conventions):
    BTC          : m/84'/0'/0'/0/{idx}     (P2WPKH bech32, BIP84)
    ETH/BSC/POLY : m/44'/60'/0'/0/{idx}
    TRON         : m/44'/195'/0'/0/{idx}
    TON          : m/44'/607'/0'/0/{idx}
    SOL          : m/44'/501'/{idx}'/0'    (Solana convention)

All derivations are deterministic — given the same operator seed and
``derivation_index``, the same address is reproduced. This is the standard
deposit-address pattern used by every major exchange.
"""
from __future__ import annotations

from dataclasses import dataclass

from bip_utils import (
    Bip32Slip10Ed25519,
    Bip44,
    Bip44Changes,
    Bip44Coins,
    Bip84,
    Bip84Coins,
)

from ..db.models import Chain
from .seed import get_seed_bytes


@dataclass(frozen=True)
class DerivedKey:
    address: str
    private_key_hex: str
    public_key_hex: str


def _derive_bip44(seed: bytes, coin: Bip44Coins, index: int) -> DerivedKey:
    ctx = (
        Bip44.FromSeed(seed, coin)
        .Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(index)
    )
    return DerivedKey(
        address=ctx.PublicKey().ToAddress(),
        private_key_hex=ctx.PrivateKey().Raw().ToHex(),
        public_key_hex=ctx.PublicKey().RawCompressed().ToHex(),
    )


def derive_btc(index: int) -> DerivedKey:
    ctx = (
        Bip84.FromSeed(get_seed_bytes(), Bip84Coins.BITCOIN)
        .Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(index)
    )
    return DerivedKey(
        address=ctx.PublicKey().ToAddress(),
        private_key_hex=ctx.PrivateKey().Raw().ToHex(),
        public_key_hex=ctx.PublicKey().RawCompressed().ToHex(),
    )


def derive_evm(index: int) -> DerivedKey:
    return _derive_bip44(get_seed_bytes(), Bip44Coins.ETHEREUM, index)


def derive_tron(index: int) -> DerivedKey:
    return _derive_bip44(get_seed_bytes(), Bip44Coins.TRON, index)


def derive_ton(index: int) -> DerivedKey:
    return _derive_bip44(get_seed_bytes(), Bip44Coins.TON, index)


def derive_solana(index: int) -> DerivedKey:
    # Solana uses ed25519 + path m/44'/501'/index'/0'
    path = f"m/44'/501'/{index}'/0'"
    ctx = Bip32Slip10Ed25519.FromSeed(get_seed_bytes()).DerivePath(path)
    pub = ctx.PublicKey().RawCompressed().ToBytes()[1:]  # strip the 0x00 prefix
    from base58 import b58encode

    return DerivedKey(
        address=b58encode(pub).decode(),
        private_key_hex=ctx.PrivateKey().Raw().ToHex(),
        public_key_hex=pub.hex(),
    )


def derive(chain: Chain, index: int) -> DerivedKey:
    if chain == Chain.BTC:
        return derive_btc(index)
    if chain in (Chain.ETH, Chain.BSC, Chain.POLYGON):
        return derive_evm(index)
    if chain == Chain.TRON:
        return derive_tron(index)
    if chain == Chain.TON:
        return derive_ton(index)
    if chain == Chain.SOL:
        return derive_solana(index)
    raise ValueError(f"unsupported chain: {chain}")
