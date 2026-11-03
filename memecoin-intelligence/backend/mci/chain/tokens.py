"""Own on-chain security analysis of a token mint (no third-party scoring service).

Input: the ``getAccountInfo`` (jsonParsed) value of the mint and, for classic SPL tokens, the raw Metaplex
metadata account. Output: a list of findings with a severity:

* ``critical`` / ``high``  -> hard exclusion (the token is never bought, whatever its opportunity score);
* ``medium``               -> reported as a risk;
* ``info``                 -> shown for transparency.

Unknown Token-2022 extensions or an unknown owner program are never treated as safe.
"""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass, field
from typing import Any

from mci.chain.borsh import Reader

TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
BLOCKING = ("critical", "high")


@dataclass
class Finding:
    code: str
    severity: str  # critical | high | medium | info
    message: str  # Italian, shown to the user

    @property
    def blocking(self) -> bool:
        return self.severity in BLOCKING


@dataclass
class MintSecurity:
    mint: str
    program: str | None = None
    decimals: int | None = None
    supply_raw: int | None = None
    mint_authority: str | None = None
    freeze_authority: str | None = None
    extensions: list[str] = field(default_factory=list)
    metadata_mutable: bool | None = None
    metadata_update_authority: str | None = None
    name: str | None = None
    symbol: str | None = None
    uri: str | None = None
    findings: list[Finding] = field(default_factory=list)
    complete: bool = False  # False when the account could not be read/parsed

    @property
    def blocking(self) -> list[Finding]:
        return [f for f in self.findings if f.blocking]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["blocking"] = [f.code for f in self.blocking]
        return d


def _set(v: Any) -> bool:
    """An authority/address field is configured when it holds a real address (not null / system program)."""
    return isinstance(v, str) and v not in ("", "11111111111111111111111111111111")


def _fee_bps(state: dict[str, Any]) -> int:
    out = 0
    for k in ("newerTransferFee", "olderTransferFee"):
        try:
            out = max(out, int((state.get(k) or {}).get("transferFeeBasisPoints") or 0))
        except (TypeError, ValueError):
            pass
    return out


def _extension_findings(name: str, st: dict[str, Any], sec: MintSecurity) -> list[Finding]:
    f: list[Finding] = []
    if name == "permanentDelegate":
        if _set(st.get("delegate")):
            f.append(Finding("PERMANENT_DELEGATE", "critical",
                             "delegato permanente: un indirizzo può spostare o bruciare i token di chiunque"))
    elif name == "transferHook":
        if _set(st.get("programId")):
            f.append(Finding("TRANSFER_HOOK", "critical",
                             "transfer hook attivo: un programma esterno decide se i trasferimenti (vendite) passano"))
        elif _set(st.get("authority")):
            f.append(Finding("TRANSFER_HOOK_AUTHORITY", "high",
                             "qualcuno può attivare in qualsiasi momento un transfer hook (blocco delle vendite)"))
    elif name == "transferFeeConfig":
        bps = _fee_bps(st)
        if bps > 0:
            f.append(Finding("TRANSFER_FEE", "critical", f"tassa su ogni trasferimento del {bps / 100:.2f}%"))
        elif _set(st.get("transferFeeConfigAuthority")):
            f.append(Finding("TRANSFER_FEE_AUTHORITY", "medium",
                             "la tassa sui trasferimenti è 0 ma può essere attivata (effetto dopo ~2 epoche)"))
    elif name == "defaultAccountState":
        if str(st.get("accountState") or st.get("state") or "").lower() == "frozen":
            f.append(Finding("DEFAULT_FROZEN", "critical", "i nuovi conti token nascono congelati"))
    elif name == "nonTransferable":
        f.append(Finding("NON_TRANSFERABLE", "critical", "token non trasferibile: impossibile vendere"))
    elif name in ("pausableConfig", "pausable"):
        if st.get("paused") is True:
            f.append(Finding("PAUSED", "critical", "token in pausa: trasferimenti bloccati"))
        elif _set(st.get("authority")):
            f.append(Finding("PAUSABLE", "high", "un'autorità può mettere in pausa tutti i trasferimenti"))
    elif name == "mintCloseAuthority":
        if _set(st.get("closeAuthority")):
            f.append(Finding("MINT_CLOSE_AUTHORITY", "medium", "il mint può essere chiuso (solo a supply zero)"))
    elif name == "confidentialTransferMint":
        if _set(st.get("authority")) or st.get("autoApproveNewAccounts"):
            f.append(Finding("CONFIDENTIAL_TRANSFER", "high",
                             "trasferimenti confidenziali: saldi e concentrazione non verificabili"))
    elif name == "confidentialTransferFeeConfig":
        f.append(Finding("CONFIDENTIAL_TRANSFER_FEE", "medium", "configurazione di commissioni confidenziali"))
    elif name in ("interestBearingConfig", "scaledUiAmountConfig"):
        if _set(st.get("rateAuthority")) or _set(st.get("authority")):
            f.append(Finding("UI_AMOUNT_MUTABLE", "high",
                             "il saldo mostrato può essere moltiplicato/modificato da un'autorità"))
    elif name == "metadataPointer":
        if _set(st.get("authority")):
            f.append(Finding("METADATA_POINTER_MUTABLE", "medium", "il puntatore ai metadati può essere cambiato"))
    elif name == "tokenMetadata":
        sec.name, sec.symbol, sec.uri = st.get("name"), st.get("symbol"), st.get("uri")
        sec.metadata_update_authority = st.get("updateAuthority")
        sec.metadata_mutable = _set(st.get("updateAuthority"))
        if sec.metadata_mutable:
            f.append(Finding("METADATA_MUTABLE", "medium", "nome/simbolo/immagine modificabili dal creatore"))
    elif name in ("groupPointer", "groupMemberPointer", "tokenGroup", "tokenGroupMember", "immutableOwner",
                  "memoTransfer", "cpiGuard"):
        pass
    else:
        f.append(Finding("UNKNOWN_EXTENSION", "high", f"estensione Token-2022 non riconosciuta: {name}"))
    return f


def analyze_mint(mint: str, account: dict[str, Any] | None) -> MintSecurity:
    """``account`` is the ``value`` of getAccountInfo(mint, {"encoding": "jsonParsed"})."""
    sec = MintSecurity(mint=mint)
    if not account:
        sec.findings.append(Finding("MINT_NOT_FOUND", "high", "account del mint non trovato on-chain"))
        return sec
    sec.program = account.get("owner")
    data = account.get("data")
    parsed = data.get("parsed") if isinstance(data, dict) else None
    info = (parsed or {}).get("info") if isinstance(parsed, dict) else None
    if sec.program not in (TOKEN_PROGRAM, TOKEN_2022_PROGRAM):
        sec.findings.append(Finding("UNKNOWN_TOKEN_PROGRAM", "critical", f"programma del token sconosciuto: {sec.program}"))
        return sec
    if not isinstance(info, dict) or (parsed or {}).get("type") != "mint":
        sec.findings.append(Finding("MINT_UNPARSEABLE", "high", "dati del mint non interpretabili"))
        return sec
    sec.decimals = info.get("decimals")
    try:
        sec.supply_raw = int(info.get("supply"))
    except (TypeError, ValueError):
        sec.supply_raw = None
    sec.mint_authority = info.get("mintAuthority")
    sec.freeze_authority = info.get("freezeAuthority")
    if _set(sec.mint_authority):
        sec.findings.append(Finding("MINT_AUTHORITY_ACTIVE", "critical", "mint authority attiva: possono essere stampati nuovi token"))
    if _set(sec.freeze_authority):
        sec.findings.append(Finding("FREEZE_AUTHORITY_ACTIVE", "critical", "freeze authority attiva: i wallet possono essere congelati"))
    for ext in info.get("extensions") or []:
        if not isinstance(ext, dict):
            continue
        name = str(ext.get("extension") or "?")
        sec.extensions.append(name)
        sec.findings.extend(_extension_findings(name, ext.get("state") or {}, sec))
    sec.complete = True
    return sec


@dataclass
class MetaplexMetadata:
    update_authority: str
    mint: str
    name: str
    symbol: str
    uri: str
    seller_fee_bps: int
    creators: list[dict[str, Any]]
    primary_sale_happened: bool
    is_mutable: bool


def decode_metaplex(raw: bytes) -> MetaplexMetadata:
    r = Reader(raw)
    if r.u8() != 4:  # Key::MetadataV1
        raise ValueError("not a Metaplex MetadataV1 account")
    ua, mint = r.pubkey(), r.pubkey()
    name, symbol, uri = (r.string().rstrip("\x00").strip() for _ in range(3))
    fee = r.u16()
    creators = []
    if r.u8() == 1:
        for _ in range(r.u32()):
            creators.append({"address": r.pubkey(), "verified": r.bool(), "share": r.u8()})
    primary = r.bool()
    mutable = r.bool()
    return MetaplexMetadata(ua, mint, name, symbol, uri, fee, creators, primary, mutable)


def apply_metaplex(sec: MintSecurity, account: dict[str, Any] | None) -> MintSecurity:
    """Classic SPL tokens keep name/symbol/uri in a Metaplex account: decode it for mutability."""
    if not account:
        return sec
    data = account.get("data")
    if not (isinstance(data, list) and data and data[-1] == "base64"):
        return sec
    try:
        md = decode_metaplex(base64.b64decode(data[0]))
    except (ValueError, TypeError):
        return sec
    sec.name, sec.symbol, sec.uri = md.name, md.symbol, md.uri
    sec.metadata_update_authority = md.update_authority
    sec.metadata_mutable = md.is_mutable
    if md.is_mutable:
        sec.findings.append(Finding("METADATA_MUTABLE", "medium", "nome/simbolo/immagine modificabili dal creatore"))
    return sec
