"""HD-derivation regression tests.

We assert against the well-known BIP39 vector
``abandon abandon ... about`` (the canonical test mnemonic). These tests
guard us against silent regressions in derivation that would break the
deposit address contract.
"""
from __future__ import annotations

import os

from cryptography.fernet import Fernet


def _setup_test_env() -> None:
    """Populate env so app.crypto.seed.decrypt_mnemonic returns the test mnemonic."""
    mnemonic = (
        "abandon abandon abandon abandon abandon abandon abandon abandon "
        "abandon abandon abandon about"
    )
    key = Fernet.generate_key().decode()
    blob = Fernet(key.encode()).encrypt(mnemonic.encode()).decode()
    os.environ["MASTER_KEY"] = key
    os.environ["MASTER_SEED_ENCRYPTED"] = blob


def test_derivation_matches_canonical_vectors() -> None:
    _setup_test_env()
    # Re-import after env is set so settings cache picks up new values.
    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    from app.crypto import hd, seed

    seed.get_seed_bytes.cache_clear()  # type: ignore[attr-defined]

    assert hd.derive_btc(0).address == "bc1qcr8te4kr609gcawutmrza0j4xv80jy8z306fyu"
    assert hd.derive_evm(0).address == "0x9858EfFD232B4033E47d90003D41EC34EcaEda94"
    # Distinct indices yield distinct addresses (no collisions).
    assert hd.derive_btc(1).address != hd.derive_btc(0).address
    assert hd.derive_tron(0).address.startswith("T")
    assert hd.derive_ton(0).address  # non-empty
    assert hd.derive_solana(0).address  # non-empty


def test_seed_encrypt_decrypt_roundtrip() -> None:
    from cryptography.fernet import Fernet as _F

    key = _F.generate_key().decode()
    os.environ["MASTER_KEY"] = key

    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    from app.crypto.seed import decrypt_mnemonic, encrypt_mnemonic

    m = "test mnemonic words"
    enc = encrypt_mnemonic(m)
    assert decrypt_mnemonic(enc) == m
