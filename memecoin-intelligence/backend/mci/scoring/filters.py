"""Hard exclusion rules, applied BEFORE scoring.

A token that fails any rule is never bought, whatever its score.
When ``for_trading=True`` a missing critical datum is itself an exclusion
("dati insufficienti"): unknown is never treated as safe.
"""

from __future__ import annotations

from dataclasses import dataclass

from mci.domain import TokenSnapshot

LAUNCHPAD_DEXES = {"pumpfun", "pump", "pumpswap", "letsbonk", "meteoradbc", "moonshot"}


@dataclass
class FilterConfig:
    min_liquidity_usd: float = 15_000.0
    max_top10_pct: float = 50.0
    max_top1_pct: float = 20.0
    max_dev_pct: float = 10.0
    max_insider_cluster_pct: float = 30.0
    max_early_cluster_pct: float = 30.0
    max_sell_impact_pct: float = 5.0
    max_wash_score: float = 0.75
    max_price_divergence_pct: float = 15.0
    min_lp_locked_pct: float = 80.0
    min_age_minutes: float = 5.0
    max_rugcheck_score_norm: float = 70.0


@dataclass
class FilterResult:
    excluded: bool
    reasons: list[str]  # human readable (Italian)
    codes: list[str]
    pending_checks: list[str]  # data needed before the token can be traded


def evaluate_filters(s: TokenSnapshot, cfg: FilterConfig | None = None, for_trading: bool = False) -> FilterResult:
    cfg = cfg or FilterConfig()
    reasons: list[str] = []
    codes: list[str] = []
    pending: list[str] = []

    def fail(code: str, msg: str) -> None:
        codes.append(code)
        reasons.append(msg)

    # --- contract security ----------------------------------------------------
    if s.rugged_flag is True:
        fail("RUGGED", "token segnalato come già 'ruggato'")
    if s.mint_authority_revoked is False:
        fail("MINT_AUTHORITY_ACTIVE", "mint authority attiva: il creatore può stampare nuovi token")
    elif s.mint_authority_revoked is None:
        pending.append("mint_authority")
    if s.freeze_authority_revoked is False:
        fail("FREEZE_AUTHORITY_ACTIVE", "freeze authority attiva: i wallet possono essere congelati (honeypot)")
    elif s.freeze_authority_revoked is None:
        pending.append("freeze_authority")
    blocking = [x for x in (s.onchain_findings or []) if x.get("blocking")]
    if blocking:
        fail("ONCHAIN_SECURITY", "controllo on-chain: " + "; ".join(str(x.get("message")) for x in blocking[:3]))
    if s.bonding_curve and s.mayhem:
        fail("MAYHEM_CURVE", "curva 'mayhem' di pump.fun: prezzo mosso da un agente, dinamica non organica")
    if s.sell_sim_ok is False:
        fail("SELL_SIM_FAILED", "la vendita simulata on-chain di un holder reale fallisce"
             + (f" ({s.sell_sim_detail})" if s.sell_sim_detail else ""))
    if s.dangerous_extensions:
        fail("DANGEROUS_EXTENSION", "estensioni Token-2022 pericolose: " + ", ".join(s.dangerous_extensions))
    danger = [r.get("name") for r in s.rugcheck_risks if (r.get("level") or "") == "danger"]
    if danger:
        fail("RUGCHECK_DANGER", "rischi critici RugCheck: " + ", ".join(str(d) for d in danger[:4]))
    if s.rugcheck_score_norm is not None and s.rugcheck_score_norm > cfg.max_rugcheck_score_norm:
        fail("RUGCHECK_SCORE", f"punteggio di rischio RugCheck elevato ({s.rugcheck_score_norm:.0f}/100)")

    # --- sellability / honeypot ----------------------------------------------
    if s.sell_route_ok is False:
        fail("HONEYPOT_NO_SELL_ROUTE", "nessuna rotta di vendita disponibile (possibile honeypot)")
    elif s.sell_route_ok is None:
        pending.append("sell_route")
    if s.sell_impact_pct is not None and s.sell_impact_pct > cfg.max_sell_impact_pct:
        fail("SELL_IMPACT", f"impatto di prezzo in vendita eccessivo ({s.sell_impact_pct:.1f}%)")

    # --- liquidity ------------------------------------------------------------
    if s.liquidity_usd is None and s.liquidity_quote is None:
        pending.append("liquidity")
    elif s.liquidity_usd is not None and s.liquidity_usd < cfg.min_liquidity_usd:
        fail("LOW_LIQUIDITY", f"liquidità insufficiente ({s.liquidity_usd:,.0f} $ < {cfg.min_liquidity_usd:,.0f} $)")
    dex = (s.dex_id or "").lower()
    if dex and dex not in LAUNCHPAD_DEXES and not s.bonding_curve:
        if s.lp_locked_pct is not None and s.lp_locked_pct < cfg.min_lp_locked_pct:
            fail("LP_UNLOCKED", f"LP bloccata/bruciata solo al {s.lp_locked_pct:.0f}%")
        elif s.lp_locked_pct is None:
            pending.append("lp_lock")

    # --- concentration --------------------------------------------------------
    if s.top10_pct is None:
        pending.append("holders")
    else:
        if s.top10_pct > cfg.max_top10_pct:
            fail("TOP10_CONCENTRATION", f"top 10 holder detengono il {s.top10_pct:.1f}% della supply")
        if s.top1_pct is not None and s.top1_pct > cfg.max_top1_pct:
            fail("TOP1_CONCENTRATION", f"un singolo holder detiene il {s.top1_pct:.1f}%")
    if s.dev_pct is not None and s.dev_pct > cfg.max_dev_pct:
        fail("DEV_HOLDING", f"il deployer detiene il {s.dev_pct:.1f}%")
    if s.insider_cluster_pct is not None and s.insider_cluster_pct > cfg.max_insider_cluster_pct:
        fail("INSIDER_CLUSTER", f"cluster di insider con il {s.insider_cluster_pct:.1f}% della supply")
    if s.early_buyer_cluster_pct is not None and s.early_buyer_cluster_pct > cfg.max_early_cluster_pct:
        fail("EARLY_CLUSTER", f"sniper/bundle iniziali con il {s.early_buyer_cluster_pct:.1f}% della supply")

    # --- market integrity -----------------------------------------------------
    if s.wash_score is not None and s.wash_score >= cfg.max_wash_score:
        fail("WASH_TRADING", f"manipolazione del volume evidente (wash score {s.wash_score:.2f})")
    if s.price_divergence_pct is not None and s.price_divergence_pct > cfg.max_price_divergence_pct:
        fail("PRICE_ANOMALY", f"prezzi divergenti tra le fonti ({s.price_divergence_pct:.1f}%)")
    if s.price_usd is None and s.price_native is None:
        pending.append("price")

    age = s.age_minutes
    if age is None:
        pending.append("age")
    elif age < cfg.min_age_minutes:
        # temporary condition: not tradable yet, but not a safety failure
        if for_trading:
            fail("TOO_YOUNG", f"token troppo giovane ({age:.0f} min)")
        else:
            pending.append("età minima")

    if for_trading and pending:
        fail("INSUFFICIENT_DATA", "dati insufficienti per operare: " + ", ".join(sorted(set(pending))))

    return FilterResult(excluded=bool(codes), reasons=reasons, codes=codes, pending_checks=sorted(set(pending)))
