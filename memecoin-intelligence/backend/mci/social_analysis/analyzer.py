"""Classify the *type* of attention a token receives.

With free data in 2026, authenticity is estimated mostly ON-CHAIN (unique buyers,
distribution, trades per trader) and only secondarily from social sources.
Categories (RESEARCH_REPORT §8):

* ``organic``         many unique buyers, healthy distribution, low wash score
* ``paid_marketing``  paid boosts/profiles without broadening buyer base
* ``artificial``      volume driven by few wallets / wash trading
* ``coordinated``     concentrated early buying (sniper/bundle) or cluster holdings
* ``suspicious``      coordinated selling / insider activity
* ``unknown``         not enough data - NEVER treated as positive
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mci.domain import TokenSnapshot


@dataclass
class AttentionAssessment:
    category: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    social_coverage: float = 0.0  # share of social sources that returned data


def assess_attention(s: TokenSnapshot) -> AttentionAssessment:
    ev: list[str] = []
    buyers_h1 = s.buyers.get("h1")
    buys_h1 = s.buys.get("h1")
    sm = s.social_metrics or {}

    social_sources = ["reddit", "telegram_members"]
    covered = sum(1 for k in social_sources if sm.get(k) is not None)
    coverage = covered / len(social_sources)

    if s.wash_score is not None and s.wash_score >= 0.6:
        ev.append(f"wash score elevato ({s.wash_score:.2f})")
        return AttentionAssessment("artificial", 0.7, ev, coverage)

    if (s.early_buyer_cluster_pct or 0) >= 15 or (s.insider_cluster_pct or 0) >= 20:
        ev.append("acquisti iniziali/insider concentrati")
        return AttentionAssessment("coordinated", 0.6, ev, coverage)

    if sm.get("coordinated_selling"):
        ev.append("vendite coordinate dei top holder")
        return AttentionAssessment("suspicious", 0.7, ev, coverage)

    if buyers_h1 is None and buys_h1 is None:
        return AttentionAssessment("unknown", 0.0, ["dati sui compratori non disponibili"], coverage)

    unique_ratio = None
    if buyers_h1 is not None and buys_h1:
        unique_ratio = buyers_h1 / max(buys_h1, 1)

    paid = bool(s.boosts_active) or bool(s.has_profile)
    broad = (buyers_h1 or 0) >= 150 and (unique_ratio is None or unique_ratio >= 0.35)
    if broad and (s.top10_pct is None or s.top10_pct <= 30):
        ev.append(f"{buyers_h1} compratori unici in 1h")
        if unique_ratio is not None:
            ev.append(f"rapporto compratori unici/acquisti {unique_ratio:.2f}")
        reddit = sm.get("reddit") or {}
        if reddit.get("unique_authors", 0) >= 5:
            ev.append(f"{reddit['unique_authors']} autori distinti su Reddit (24h)")
        return AttentionAssessment("organic", 0.5 + 0.2 * coverage, ev, coverage)

    if paid:
        ev.append("promozione a pagamento attiva (boost/profilo) senza base di compratori ampia")
        return AttentionAssessment("paid_marketing", 0.5, ev, coverage)

    if unique_ratio is not None and unique_ratio < 0.2:
        ev.append(f"pochi wallet generano molte transazioni (rapporto {unique_ratio:.2f})")
        return AttentionAssessment("artificial", 0.5, ev, coverage)

    return AttentionAssessment("unknown", 0.2, ev or ["segnali insufficienti per classificare"], coverage)
