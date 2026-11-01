"""Dedicated-wallet key handling for LIVE mode.

Rules (see docs/SECURITY.md):
* the key is read from a keypair file OUTSIDE the repository (Solana CLI JSON format),
  readable only by the service user (chmod 600); never from code, logs or git;
* the private key is never printed: ``repr``/``str`` show only the public key;
* only a DEDICATED wallet funded with limited capital must be used - never the main wallet.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any


class WalletError(Exception):
    pass


class DedicatedWallet:
    def __init__(self, keypair: Any):
        self._kp = keypair

    @property
    def pubkey(self) -> str:
        return str(self._kp.pubkey())

    def sign_versioned_tx(self, tx_base64: str) -> str:
        import base64

        from solders.transaction import VersionedTransaction  # type: ignore[import-not-found]

        raw = VersionedTransaction.from_bytes(base64.b64decode(tx_base64))
        signed = VersionedTransaction(raw.message, [self._kp])
        return base64.b64encode(bytes(signed)).decode()

    def __repr__(self) -> str:
        return f"DedicatedWallet(pubkey={self.pubkey})"

    __str__ = __repr__


def load_wallet(path: str) -> DedicatedWallet:
    p = Path(path).expanduser()
    if not p.exists():
        raise WalletError("file del keypair non trovato")
    repo_root = Path(__file__).resolve().parents[3]
    if repo_root in p.resolve().parents:
        raise WalletError("il keypair non deve trovarsi dentro la cartella del progetto/repository")
    mode = p.stat().st_mode
    if os.name == "posix" and mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise WalletError("permessi del keypair troppo aperti: usare chmod 600")
    try:
        from solders.keypair import Keypair  # type: ignore[import-not-found]
    except ImportError as e:  # pragma: no cover - optional dependency
        raise WalletError("dipendenza 'solders' non installata (pip install '.[live]')") from e
    try:
        data = json.loads(p.read_text())
        kp = Keypair.from_bytes(bytes(data))
    except Exception as e:  # never include file content in the error
        raise WalletError("keypair non valido") from e
    return DedicatedWallet(kp)
