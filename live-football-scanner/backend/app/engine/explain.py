"""Human-readable statistical reasons and risk factors (Italian). Only observed data is cited."""
from __future__ import annotations

from .features import OriginState
from .forecast import Forecast
from .value import DataQuality, Evaluation

KNOCKOUT_WORDS = ("final", "semi", "quarter", "round of", "knockout", "play-off", "playoff", "1/8", "1/4", "1/2")


def _pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def _rate10(cum: float | None, minutes: float) -> float | None:
    if cum is None or minutes <= 0:
        return None
    return cum / minutes * 10.0


def intensity(state: OriginState) -> dict:
    """Per-side recent vs. match-average attacking output (per 10 minutes)."""
    mins = max(state.minutes_played(), 1.0)
    out = {}
    for side, obs, win in (("home", state.home, state.home_w10), ("away", state.away, state.away_w10)):
        d = {}
        for k in ("shots", "sot", "corners", "xg"):
            avg = _rate10(getattr(obs, k), mins)
            rec = getattr(win, k) if win is not None else None
            d[k] = {"last10": rec, "avg10": None if avg is None else round(avg, 2)}
        out[side] = d
    return out


def fixture_reasons(sel_market: str, pick: str, state: OriginState, fc: Forecast, home: str, away: str,
                    ev: Evaluation) -> list[str]:
    r: list[str] = []
    eh = float(fc.exp_goals_home.mean())
    ea = float(fc.exp_goals_away.mean())
    p_more = 1.0 - float(fc.p_next_none.mean())
    inten = intensity(state)
    goals_market = sel_market in ("total_goals", "btts", "goal_next_10", "goal_2h", "team_goals_home",
                                  "team_goals_away", "ht_total_goals", "correct_score")
    if goals_market:
        r.append(f"Gol attesi nel resto della partita: {eh + ea:.2f} ({home} {eh:.2f}, {away} {ea:.2f}); "
                 f"P(almeno un altro gol) = {_pct(p_more)}")
    if sel_market in ("1x2", "dnb", "double_chance", "ht_1x2", "next_goal"):
        r.append(f"Prossimo gol: {home} {_pct(float(fc.p_next_home.mean()))}, {away} "
                 f"{_pct(float(fc.p_next_away.mean()))}, nessuno {_pct(float(fc.p_next_none.mean()))}")
    for side, name in (("home", home), ("away", away)):
        d = inten[side]
        sot, sh = d["sot"], d["shots"]
        if sot["last10"] is not None and sot["avg10"] is not None:
            if sot["last10"] >= max(2, 1.5 * sot["avg10"]):
                r.append(f"{name}: {sot['last10']:.0f} tiri in porta negli ultimi 10' "
                         f"(media partita {sot['avg10']:.1f} ogni 10')")
            elif sh["last10"] is not None and sh["avg10"] is not None and sh["last10"] >= max(3, 1.5 * sh["avg10"]):
                r.append(f"{name}: {sh['last10']:.0f} tiri negli ultimi 10' (media {sh['avg10']:.1f})")
        if d["xg"]["last10"] is not None and d["xg"]["last10"] >= 0.4:
            r.append(f"{name}: xG {d['xg']['last10']:.2f} negli ultimi 10'")
    diff = state.home.goals - state.away.goals
    if state.period == 2 and state.clock >= 65 and diff != 0:
        trailing = away if diff > 0 else home
        r.append(f"{trailing} in svantaggio dopo il 65': storicamente la squadra sotto aumenta la produzione offensiva")
    adv = (state.away.reds or 0) - (state.home.reds or 0)
    if adv != 0:
        up = home if adv > 0 else away
        r.append(f"Superiorità numerica per {up} ({abs(adv)} espulsione/i avversaria/e)")
    for side, name, pr in (("home", home, state.home_prior), ("away", away, state.away_prior)):
        if pr.n_matches >= 5 and abs(pr.att) > 0.2:
            r.append(f"Forma pre-partita {name}: attacco {'sopra' if pr.att > 0 else 'sotto'} la media "
                     f"({pr.n_matches} partite)")
    if sel_market == "total_corners":
        for side, name in (("home", home), ("away", away)):
            c = inten[side]["corners"]
            if c["last10"] is not None and c["avg10"] is not None and c["last10"] >= max(2, 1.5 * c["avg10"]):
                r.append(f"{name}: {c['last10']:.0f} corner negli ultimi 10' (media {c['avg10']:.1f})")
        if fc.corners_home is not None:
            r.append(f"Corner attesi nel resto della partita: {float((fc.corners_home + fc.corners_away).mean()):.1f}")
    fair = f", equa di mercato {_pct(ev.p_market_fair)}" if ev.p_market_fair is not None else ""
    r.append(f"Probabilità stimata {_pct(ev.p_model)} (intervallo 10-90%: {_pct(ev.p_low)}-{_pct(ev.p_high)}) "
             f"contro implicita {_pct(ev.implied)}{fair}")
    r.append(f"EV teorico {ev.ev:+.1%}, EV prudenziale {ev.ev_cons:+.1%} (margine di validazione "
             f"{100 * ev.margin:.1f} pp)")
    return r


def risk_factors(ev: Evaluation, state: OriginState, dq: DataQuality, minutes_left: float, round_name: str | None,
                 source_has_state: bool, last_red_minute: float | None) -> list[str]:
    k: list[str] = []
    if ev.odds < 1.85:
        k.append("Quota vicina alla soglia minima di 1.75: piccoli movimenti annullano il valore")
    if dq.window_minutes is None:
        k.append("Andamento ultimi 10' non disponibile (scanner avviato a partita in corso): usato il ritmo medio")
    elif dq.window_minutes < 10:
        k.append(f"Storico snapshot di soli {dq.window_minutes:.0f}': finestre recenti parziali")
    if not dq.has_xg:
        k.append("xG live non forniti per questa partita: modello basato su tiri / tiri in porta / corner")
    if dq.prior_home_n < 5 or dq.prior_away_n < 5:
        k.append("Forma pre-partita incompleta: forza delle squadre stimata con forte shrinkage")
    if ev.p_market_fair is not None:
        gap = ev.p_model / max(1e-9, 1 - ev.p_push) - ev.p_market_fair
        if abs(gap) >= 0.06:
            k.append(f"Il modello si discosta di {100 * gap:+.0f} pp dal mercato: il mercato può incorporare "
                     "informazioni non osservate (infortuni, cambi, condizioni)")
    if ev.overround is not None and ev.overround > 0.08:
        k.append(f"Margine del bookmaker elevato ({100 * ev.overround:.1f}%)")
    if minutes_left < 12:
        k.append(f"Restano circa {minutes_left:.0f}' (incluso recupero stimato): esito ad alta varianza")
    if last_red_minute is not None and state.clock - last_red_minute < 10:
        k.append("Espulsione recente: equilibrio tattico non ancora stabilizzato")
    if not source_has_state:
        k.append("Fonte quote senza stato partita: possibile ritardo rispetto agli eventi in campo")
    if ev.p_high - ev.p_low > 0.12:
        k.append(f"Incertezza parametrica ampia (intervallo {100 * (ev.p_high - ev.p_low):.0f} pp)")
    if round_name and any(w in round_name.lower() for w in KNOCKOUT_WORDS):
        k.append("Gara a eliminazione diretta: il mercato si chiude al 90'+recupero; motivazioni tattiche non modellate")
    k.append("Non modellati: infortuni, sostituzioni, motivazioni di classifica, meteo")
    return k
