"""pump.fun program: official events and the bonding-curve account.

Layouts follow the official Anchor IDL (github.com/pump-fun/pump-public-docs, idl/pump.json) and were checked
against real mainnet data (tests/fixtures/live). Decoding is tolerant: fields appended to the IDL in the future
are ignored, and a truncated tail never invents values.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any

from mci.chain.borsh import Reader

PUMP_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
# program that trades "mayhem mode" tokens on behalf of pump.fun (seen in real mayhem trades): not an organic buyer
MAYHEM_PROGRAM_ID = "MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e"
NATIVE_QUOTES = {"11111111111111111111111111111111", "So11111111111111111111111111111111111111112"}
TRADE_EVENT = bytes.fromhex("bddb7fd34ee661ee")
CREATE_EVENT = bytes.fromhex("1b72a94ddeeb6376")
COMPLETE_EVENT = bytes.fromhex("5f72619cd42e9808")
MIGRATION_EVENT = bytes.fromhex("bde95db95c94ea94")
BONDING_CURVE_DISC = bytes.fromhex("17b7f83760d8ac60")
TOKEN_DECIMALS = 6
LAMPORTS = 1_000_000_000


# Field layouts (name, type) our decoders rely on, in order: a prefix of the official IDL layouts. Fields
# appended later by pump.fun are ignored; any change inside this prefix is caught by scripts/contract_check.py
# (weekly GitHub workflow) and by tests/test_chain.py.
TRADE_EVENT_LAYOUT = [
    ("mint", "pubkey"), ("sol_amount", "u64"), ("token_amount", "u64"), ("is_buy", "bool"), ("user", "pubkey"),
    ("timestamp", "i64"), ("virtual_sol_reserves", "u64"), ("virtual_token_reserves", "u64"),
    ("real_sol_reserves", "u64"), ("real_token_reserves", "u64"), ("fee_recipient", "pubkey"),
    ("fee_basis_points", "u64"), ("fee", "u64"), ("creator", "pubkey"), ("creator_fee_basis_points", "u64"),
    ("creator_fee", "u64"), ("track_volume", "bool"), ("total_unclaimed_tokens", "u64"),
    ("total_claimed_tokens", "u64"), ("current_sol_volume", "u64"), ("last_update_timestamp", "i64"),
    ("ix_name", "string"), ("mayhem_mode", "bool"), ("cashback_fee_basis_points", "u64"), ("cashback", "u64"),
    ("buyback_fee_basis_points", "u64"), ("buyback_fee", "u64"), ("shareholders", "vec<Shareholder>"),
    ("quote_mint", "pubkey"),
]
CREATE_EVENT_LAYOUT = [
    ("name", "string"), ("symbol", "string"), ("uri", "string"), ("mint", "pubkey"), ("bonding_curve", "pubkey"),
    ("user", "pubkey"), ("creator", "pubkey"), ("timestamp", "i64"), ("virtual_token_reserves", "u64"),
    ("virtual_sol_reserves", "u64"), ("real_token_reserves", "u64"), ("token_total_supply", "u64"),
    ("token_program", "pubkey"), ("is_mayhem_mode", "bool"), ("is_cashback_enabled", "bool"), ("quote_mint", "pubkey"),
]
COMPLETE_EVENT_LAYOUT = [("user", "pubkey"), ("mint", "pubkey"), ("bonding_curve", "pubkey"), ("timestamp", "i64")]
BONDING_CURVE_LAYOUT = [
    ("virtual_token_reserves", "u64"), ("virtual_quote_reserves", "u64"), ("real_token_reserves", "u64"),
    ("real_quote_reserves", "u64"), ("token_total_supply", "u64"), ("complete", "bool"), ("creator", "pubkey"),
    ("is_mayhem_mode", "bool"), ("is_cashback_coin", "bool"), ("quote_mint", "pubkey"), ("creator_fee_bps", "u64"),
    ("can_edit_creator_fee", "bool"), ("is_holder_reward", "bool"), ("creator_fee", "u64"), ("protocol_fees", "u64"),
    ("depth", "u8"), ("initial_virtual_quote_reserves", "u64"),
]
LAYOUTS = {"TradeEvent": (TRADE_EVENT, TRADE_EVENT_LAYOUT), "CreateEvent": (CREATE_EVENT, CREATE_EVENT_LAYOUT),
           "CompleteEvent": (COMPLETE_EVENT, COMPLETE_EVENT_LAYOUT),
           "BondingCurve": (BONDING_CURVE_DISC, BONDING_CURVE_LAYOUT)}


def _idl_type(t) -> str:
    if isinstance(t, str):
        return t
    if isinstance(t, dict) and "vec" in t:
        inner = t["vec"]
        name = inner.get("defined", {}).get("name") if isinstance(inner, dict) else inner
        return f"vec<{name}>"
    return str(t)


def check_idl(idl: dict) -> list[str]:
    """Differences between the official IDL and the layouts our decoders rely on (empty list = compatible)."""
    problems = []
    types = {t["name"]: t for t in idl.get("types", [])}
    discs = {e["name"]: bytes(e["discriminator"]) for e in idl.get("events", []) + idl.get("accounts", [])}
    for name, (disc, layout) in LAYOUTS.items():
        if discs.get(name) != disc:
            problems.append(f"{name}: discriminatore cambiato ({discs.get(name, b'').hex()} != {disc.hex()})")
        t = types.get(name)
        if not t:
            problems.append(f"{name}: tipo assente dall'IDL")
            continue
        fields = [(f["name"], _idl_type(f["type"])) for f in t["type"]["fields"]]
        if fields[: len(layout)] != layout:
            for i, (want, got) in enumerate(zip(layout, fields[: len(layout)] + [None] * len(layout))):
                if want != got:
                    problems.append(f"{name}: campo {i} atteso {want}, trovato {got}")
                    break
    return problems


def price_sol(virtual_sol: int, virtual_tokens: int) -> float | None:
    """SOL per whole token implied by the constant-product virtual reserves (SOL 9 decimals, token 6)."""
    if virtual_sol <= 0 or virtual_tokens <= 0:
        return None
    return (virtual_sol / LAMPORTS) / (virtual_tokens / 10**TOKEN_DECIMALS)


@dataclass
class TradeEvent:
    mint: str
    sol_amount: int
    token_amount: int
    is_buy: bool
    user: str
    timestamp: int
    virtual_sol_reserves: int
    virtual_token_reserves: int
    real_sol_reserves: int
    real_token_reserves: int
    creator: str | None = None
    fee: int | None = None
    creator_fee: int | None = None
    ix_name: str | None = None
    mayhem_mode: bool | None = None
    quote_mint: str | None = None
    signature: str | None = None
    slot: int | None = None
    agent: bool = False  # executed through pump.fun's mayhem agent program (not an organic buyer)

    @property
    def sol(self) -> float:
        return self.sol_amount / LAMPORTS

    @property
    def tokens(self) -> float:
        return self.token_amount / 10**TOKEN_DECIMALS

    @property
    def price(self) -> float | None:
        """Price after the trade, in SOL per token (None when the curve is quoted in another token)."""
        if self.quote_mint and self.quote_mint not in NATIVE_QUOTES:
            return None
        return price_sol(self.virtual_sol_reserves, self.virtual_token_reserves)


@dataclass
class CreateEvent:
    name: str
    symbol: str
    uri: str
    mint: str
    bonding_curve: str
    user: str
    creator: str
    timestamp: int
    virtual_token_reserves: int | None = None
    virtual_sol_reserves: int | None = None
    real_token_reserves: int | None = None
    token_total_supply: int | None = None
    token_program: str | None = None
    is_mayhem_mode: bool | None = None
    quote_mint: str | None = None
    signature: str | None = None
    slot: int | None = None


@dataclass
class CompleteEvent:
    user: str
    mint: str
    bonding_curve: str
    timestamp: int
    signature: str | None = None
    slot: int | None = None


@dataclass
class BondingCurveState:
    virtual_token_reserves: int
    virtual_quote_reserves: int
    real_token_reserves: int
    real_quote_reserves: int
    token_total_supply: int
    complete: bool
    creator: str | None = None
    is_mayhem_mode: bool | None = None
    is_cashback_coin: bool | None = None
    quote_mint: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def price(self) -> float | None:
        """Constant-product price. Not reliable for "mayhem mode" curves: observed on mainnet (Nov 2026) their
        virtual reserves move without a matching real SOL reserve (pump.fun's agent trades them), so None."""
        if self.is_mayhem_mode or (self.quote_mint and self.quote_mint not in NATIVE_QUOTES):
            return None
        return price_sol(self.virtual_quote_reserves, self.virtual_token_reserves)


def decode_trade(data: bytes) -> TradeEvent:
    r = Reader(data, 8)
    ev = TradeEvent(
        mint=r.pubkey(), sol_amount=r.u64(), token_amount=r.u64(), is_buy=r.bool(), user=r.pubkey(),
        timestamp=r.i64(), virtual_sol_reserves=r.u64(), virtual_token_reserves=r.u64(), real_sol_reserves=r.u64(),
        real_token_reserves=r.u64(),
    )
    try:  # tail fields (added over time): never fail the core decode because of them
        r.pubkey()  # fee_recipient
        r.u64()  # fee_basis_points
        ev.fee = r.u64()
        ev.creator = r.pubkey()
        r.u64()  # creator_fee_basis_points
        ev.creator_fee = r.u64()
        r.bool(), r.u64(), r.u64(), r.u64(), r.i64()  # volume tracking
        ev.ix_name = r.string()
        ev.mayhem_mode = r.bool()
        r.u64(), r.u64(), r.u64(), r.u64()  # cashback / buyback
        for _ in range(r.u32()):  # shareholders: (pubkey, u16)
            r.pubkey(), r.u16()
        ev.quote_mint = r.pubkey()
    except ValueError:
        pass
    return ev


def decode_create(data: bytes) -> CreateEvent:
    r = Reader(data, 8)
    ev = CreateEvent(name=r.string(), symbol=r.string(), uri=r.string(), mint=r.pubkey(), bonding_curve=r.pubkey(),
                     user=r.pubkey(), creator=r.pubkey(), timestamp=r.i64())
    try:
        ev.virtual_token_reserves = r.u64()
        ev.virtual_sol_reserves = r.u64()
        ev.real_token_reserves = r.u64()
        ev.token_total_supply = r.u64()
        ev.token_program = r.pubkey()
        ev.is_mayhem_mode = r.bool()
        r.bool()  # is_cashback_enabled
        ev.quote_mint = r.pubkey()
    except ValueError:
        pass
    return ev


def decode_complete(data: bytes) -> CompleteEvent:
    r = Reader(data, 8)
    return CompleteEvent(user=r.pubkey(), mint=r.pubkey(), bonding_curve=r.pubkey(), timestamp=r.i64())


def decode_bonding_curve(raw: bytes) -> BondingCurveState:
    if raw[:8] != BONDING_CURVE_DISC:
        raise ValueError("not a pump.fun BondingCurve account")
    r = Reader(raw, 8)
    st = BondingCurveState(virtual_token_reserves=r.u64(), virtual_quote_reserves=r.u64(), real_token_reserves=r.u64(),
                           real_quote_reserves=r.u64(), token_total_supply=r.u64(), complete=r.bool())
    try:
        st.creator = r.pubkey()
        st.is_mayhem_mode = r.bool()
        st.is_cashback_coin = r.bool()
        st.quote_mint = r.pubkey()
        st.extra["creator_fee_bps"] = r.u64()
        st.extra["can_edit_creator_fee"] = r.bool()
        st.extra["is_holder_reward"] = r.bool()
        st.extra["creator_fee"] = r.u64()
        st.extra["protocol_fees"] = r.u64()
        st.extra["depth"] = r.u8()
        st.extra["initial_virtual_quote_reserves"] = r.u64()
    except ValueError:
        pass
    return st


def events_from_logs(logs: list[str] | None, signature: str | None = None, slot: int | None = None) -> list[Any]:
    """Official pump.fun events emitted in a transaction's logs ("Program data: <base64>")."""
    out: list[Any] = []
    agent = any(line.startswith(f"Program {MAYHEM_PROGRAM_ID} invoke") for line in logs or [])
    for line in logs or []:
        if not line.startswith("Program data: "):
            continue
        try:
            data = base64.b64decode(line[14:])
        except (ValueError, TypeError):
            continue
        head = data[:8]
        try:
            if head == TRADE_EVENT:
                ev = decode_trade(data)
            elif head == CREATE_EVENT:
                ev = decode_create(data)
            elif head == COMPLETE_EVENT:
                ev = decode_complete(data)
            else:
                continue
        except ValueError:
            continue
        ev.signature, ev.slot = signature, slot
        if isinstance(ev, TradeEvent):
            ev.agent = agent
        out.append(ev)
    return out
