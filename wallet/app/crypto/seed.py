"""Operator HD seed handling.

The master mnemonic is generated once, then encrypted with Fernet using
``MASTER_KEY`` from the environment and stored in ``MASTER_SEED_ENCRYPTED``.
The raw mnemonic is decrypted in-memory only when address derivation or
signing is needed.

CLI:
    python -m app.crypto.seed gen
        Generate a fresh 24-word mnemonic and a fresh Fernet key.
    python -m app.crypto.seed encrypt
        Read a mnemonic from stdin and print the encrypted blob using
        MASTER_KEY from the environment.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache

from bip_utils import Bip39Languages, Bip39MnemonicGenerator, Bip39WordsNum
from cryptography.fernet import Fernet

from ..config import get_settings


def generate_mnemonic(words: int = 24) -> str:
    n = {12: Bip39WordsNum.WORDS_NUM_12, 18: Bip39WordsNum.WORDS_NUM_18, 24: Bip39WordsNum.WORDS_NUM_24}[words]
    return Bip39MnemonicGenerator(Bip39Languages.ENGLISH).FromWordsNumber(n).ToStr()


def encrypt_mnemonic(mnemonic: str, key: str | None = None) -> str:
    settings = get_settings()
    fkey = key or settings.master_key
    if not fkey:
        raise RuntimeError("MASTER_KEY not configured")
    return Fernet(fkey.encode()).encrypt(mnemonic.encode()).decode()


def decrypt_mnemonic(blob: str | None = None, key: str | None = None) -> str:
    settings = get_settings()
    fkey = key or settings.master_key
    payload = blob or settings.master_seed_encrypted
    if not fkey or not payload:
        raise RuntimeError("MASTER_KEY or MASTER_SEED_ENCRYPTED is missing")
    return Fernet(fkey.encode()).decrypt(payload.encode()).decode()


@lru_cache
def get_seed_bytes() -> bytes:
    """Return BIP39 seed bytes derived from the encrypted operator mnemonic."""
    from bip_utils import Bip39SeedGenerator

    mnemonic = decrypt_mnemonic()
    return Bip39SeedGenerator(mnemonic).Generate()


def _cli() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "gen":
        print("Fernet key (set as MASTER_KEY):")
        print(Fernet.generate_key().decode())
        print()
        print("Mnemonic (KEEP OFFLINE, then encrypt with `encrypt`):")
        print(generate_mnemonic(24))
    elif cmd == "encrypt":
        mnemonic = os.environ.get("MNEMONIC") or sys.stdin.read().strip()
        if not mnemonic:
            print("error: mnemonic not provided (stdin or $MNEMONIC)", file=sys.stderr)
            sys.exit(1)
        print(encrypt_mnemonic(mnemonic))
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    _cli()
