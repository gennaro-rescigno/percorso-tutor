"""Program-derived addresses without native dependencies (pure-Python ed25519 on-curve test).

``find_program_address`` reproduces Solana's algorithm: sha256(seeds || bump || program_id || "ProgramDerivedAddress")
for bump = 255..0, keeping the first hash that is NOT a valid ed25519 point. The on-curve test mirrors
curve25519-dalek's ``CompressedEdwardsY::decompress`` (y reduced mod p, x recovered with sqrt_ratio_i).
"""

from __future__ import annotations

import hashlib

from mci.chain.borsh import b58decode, b58encode

_P = 2**255 - 19
_D = (-121665 * pow(121666, _P - 2, _P)) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)


def is_on_curve(b: bytes) -> bool:
    if len(b) != 32:
        return False
    y = (int.from_bytes(b, "little") & ((1 << 255) - 1)) % _P
    u = (y * y - 1) % _P
    v = (_D * y * y + 1) % _P
    # candidate root of u/v: x = u v^3 (u v^7)^((p-5)/8)
    x = (u * pow(v, 3, _P) * pow(u * pow(v, 7, _P), (_P - 5) // 8, _P)) % _P
    vx2 = (v * x * x) % _P
    if vx2 == u:
        return True
    if vx2 == (-u) % _P:
        return True  # x * sqrt(-1) is a root
    return False


def find_program_address(seeds: list[bytes], program_id: str) -> tuple[str, int]:
    pid = b58decode(program_id)
    for bump in range(255, -1, -1):
        h = hashlib.sha256(b"".join(seeds) + bytes([bump]) + pid + b"ProgramDerivedAddress").digest()
        if not is_on_curve(h):
            return b58encode(h), bump
    raise ValueError("no viable bump seed")


METAPLEX_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"


def metaplex_metadata_address(mint: str) -> str:
    return find_program_address([b"metadata", b58decode(METAPLEX_PROGRAM_ID), b58decode(mint)], METAPLEX_PROGRAM_ID)[0]


def pump_bonding_curve_address(mint: str) -> str:
    from mci.chain.pump import PUMP_PROGRAM_ID

    return find_program_address([b"bonding-curve", b58decode(mint)], PUMP_PROGRAM_ID)[0]
