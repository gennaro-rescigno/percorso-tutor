"""Strategy Ranking Engine: scores every tested strategy on credibility, not on its best return.

Input: research/ranking/registry.csv (one row per strategy, figures copied from the study reports in the
research-results branch, with source, period and number of observations) plus, when present, the CSV files that the
discovery engines write (discovery_*_test.csv). Output: STRATEGY_RANKING.csv and STRATEGY_COMPARISON.md at the
project root. Run: python research/ranking/ranking.py [folder with discovery CSV files].

Score (fixed before ranking, 0-100):
  * significance 25%: 1 if the out-of-sample 95% interval (of the per-trade mean, or of the Sharpe ratio for
    annual results) is above zero, 0.3 if only the mean is positive, otherwise 0;
  * robustness 20%: share of the stress checks passed (doubled costs, delay, neighbouring parameters...);
  * stability 15%: share of periods / halves / years with a positive result;
  * return 15%: out-of-sample mean scaled (10% per trade or 30% a year = 1, capped);
  * drawdown 15%: 1 - |max drawdown| / 100 (0.5 when unknown);
  * sample 10%: log10(observations) / 3, capped at 1;
  * a strategy that cannot be executed with free infrastructure counts half and is never "robusta";
  * status: "scartata" when the out-of-sample mean is <= 0 or unknown (score capped at 20); "positiva ma non
    eseguibile gratis" when it needs paid infrastructure; "robusta" with significance 1, robustness >= 2/3 and
    stability >= 0.6; otherwise "promettente, non dimostrata".
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def score_row(x: pd.Series) -> pd.Series:
    mean = x.oos_media_pct
    annual = x.unita == "annuo"
    lo = x.ic_basso
    if pd.isna(mean):
        sig = 0.0
    elif not pd.isna(lo) and lo > 0:
        sig = 1.0
    elif mean > 0:
        sig = 0.3
    else:
        sig = 0.0
    rob = x.verifiche_superate / x.verifiche_totali if x.verifiche_totali else 0.0
    stab = x.periodi_positivi / x.periodi_totali if x.periodi_totali else 0.0
    ret = 0.0 if pd.isna(mean) or mean <= 0 else min(1.0, mean / (30.0 if annual else 10.0))
    dd = 0.5 if pd.isna(x.maxdd_pct) else max(0.0, 1 - abs(x.maxdd_pct) / 100)
    n = 0 if pd.isna(x.n_oos) else x.n_oos
    size = min(1.0, math.log10(n) / 3) if n and n > 1 else 0.0
    s = 100 * (0.25 * sig + 0.20 * rob + 0.15 * stab + 0.15 * ret + 0.15 * dd + 0.10 * size)
    free = str(x.eseguibile_gratis).strip().lower() == "si"
    if not free:
        s *= 0.5
    if pd.isna(mean) or mean <= 0:
        status, s = "scartata", min(s, 20.0)
    elif not free:
        status = "positiva ma non eseguibile gratis"
    elif sig == 1.0 and rob >= 2 / 3 and stab >= 0.6:
        status = "robusta"
    else:
        status = "promettente, non dimostrata"
    return pd.Series({"punteggio": round(s, 1), "significativita": sig, "robustezza": round(rob, 2),
                      "stabilita": round(stab, 2), "stato": status})


def discovery_rows(folder: Path) -> pd.DataFrame:
    rows = []
    for f in sorted(folder.glob("discovery_*_test.csv")):
        t = pd.read_csv(f)
        for i, x in t.iterrows():
            rows.append({"id": f"{f.stem.split('_')[1][:2].upper()}-D{i + 1:02d}", "area": "nuovi lanci" if "launch" in f.stem else "memecoin esistenti",
                         "strategia": f"{x.ipotesi} | {x.entrata} | {x.uscita} | {x.momento_s} s | ritardo {x.ritardo_s} s",
                         "studio": f.stem.replace("_test", ""), "fonte": "jocry", "periodo_oos": "giorni di test",
                         "n_oos": x.get("test_n"), "unita": "per operazione", "oos_media_pct": x.get("test_media_%"),
                         "ic_basso": x.get("test_IC95_basso_%"), "ic_alto": x.get("test_IC95_alto_%"), "sharpe_oos": x.get("test_Sharpe_giorni"),
                         "maxdd_pct": x.get("test_maxDD_%"),
                         "verifiche_superate": int((x.get("test_stress_media_%") or -1) > 0) + int((x.get("test_ritardo30_media_%") or -1) > 0),
                         "verifiche_totali": 2, "periodi_positivi": int((x.get("test_media_%") or -1) > 0) + 1, "periodi_totali": 3,
                         "eseguibile_gratis": "si" if x.ritardo_s >= 30 else "no",
                         "note": f"scoperta {x.get('media_scoperta_%', float('nan')):.1f}%" if "media_scoperta_%" in x else ""})
    return pd.DataFrame(rows)


def main() -> None:
    reg = pd.read_csv(HERE / "registry.csv")
    if len(sys.argv) > 1:
        extra = discovery_rows(Path(sys.argv[1]))
        if not extra.empty:
            reg = pd.concat([reg, extra], ignore_index=True)
    out = pd.concat([reg, reg.apply(score_row, axis=1)], axis=1).sort_values("punteggio", ascending=False)
    out.to_csv(ROOT / "STRATEGY_RANKING.csv", index=False)
    lines = ["# STRATEGY_COMPARISON.md — Confronto e classifica delle strategie", "",
             "Generato da `research/ranking/ranking.py` a partire da `research/ranking/registry.csv` (cifre copiate dai "
             "report degli studi nel branch `research-results`). Il punteggio premia la credibilità statistica, non il "
             "rendimento più alto: formula e pesi nel docstring di `ranking.py`.", ""]
    counts = out.stato.value_counts()
    lines += [f"Strategie valutate: **{len(out)}** · robuste: **{counts.get('robusta', 0)}** · promettenti ma non "
              f"dimostrate: **{counts.get('promettente, non dimostrata', 0)}** · positive ma non eseguibili gratis: "
              f"**{counts.get('positiva ma non eseguibile gratis', 0)}** · scartate: **{counts.get('scartata', 0)}**.", ""]
    for area in ["nuovi lanci", "memecoin esistenti", "short", "funding", "crypto affermate"]:
        t = out[out.area == area]
        if t.empty:
            continue
        lines += [f"## {area.capitalize()}", "",
                  "| Pos. | Strategia | Studio | Periodo fuori campione | N | Risultato | IC 95% | Max DD | Verifiche | Stato | Punteggio |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for k, (_, x) in enumerate(t.iterrows(), 1):
            unit = "% annuo" if x.unita == "annuo" else ("% ROI" if x.unita == "ROI" else "% a operazione")
            res = "–" if pd.isna(x.oos_media_pct) else f"{x.oos_media_pct:+.1f}{unit}"
            ci = "–" if pd.isna(x.ic_basso) else (f"Sharpe [{x.ic_basso:.2f}, {x.ic_alto:.2f}]" if x.unita == "annuo"
                                                  else f"[{x.ic_basso:.1f}, {x.ic_alto:.1f}]")
            dd = "–" if pd.isna(x.maxdd_pct) else f"{x.maxdd_pct:.0f}%"
            n = "–" if pd.isna(x.n_oos) else f"{int(x.n_oos):,}"
            lines.append(f"| {k} | {x.strategia} | {x.studio} | {x.periodo_oos} | {n} | {res} | {ci} | {dd} | "
                         f"{int(x.verifiche_superate)}/{int(x.verifiche_totali)} | {x.stato} | {x.punteggio} |")
        lines.append("")
    lines += ["## Come leggere", "",
              "- **robusta**: intervallo di confidenza fuori campione sopra zero, almeno 2 verifiche su 3 superate, risultato "
              "positivo in almeno il 60% dei periodi, eseguibile con strumenti gratuiti.",
              "- **promettente, non dimostrata**: media positiva fuori campione ma senza significatività o robustezza: non "
              "va in produzione, si può solo osservare in paper trading.",
              "- **positiva ma non eseguibile gratis**: il vantaggio esiste solo con infrastruttura a pagamento (velocità).",
              "- **scartata**: media fuori campione negativa o non misurabile.",
              "- Le note di ogni riga (nel CSV) spiegano il limite principale."]
    (ROOT / "STRATEGY_COMPARISON.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out[["id", "strategia", "punteggio", "stato"]].head(12).to_string(index=False))


if __name__ == "__main__":
    main()
