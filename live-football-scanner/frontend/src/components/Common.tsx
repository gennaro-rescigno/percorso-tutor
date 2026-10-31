import type { ReactNode } from "react";

export function ConfidenceBadge({ label, score }: { label: string; score?: number }) {
  const map: Record<string, { cls: string; text: string; icon: string }> = {
    alta: { cls: "good", text: "Alta confidenza statistica", icon: "▲" },
    media: { cls: "warning", text: "Media confidenza statistica", icon: "■" },
    bassa: { cls: "critical", text: "Bassa confidenza statistica", icon: "▼" },
  };
  const m = map[label] ?? map.bassa;
  return (
    <span className="badge" title={score !== undefined ? `Punteggio confidenza modello ${score}/100` : undefined}>
      <span className={`dot ${m.cls}`} aria-hidden />
      <span aria-hidden className="muted">{m.icon}</span>
      {m.text}
      {score !== undefined && <span className="muted">({Math.round(score)})</span>}
    </span>
  );
}

export function Tile({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="tile">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

export function Metric({ k, v, cls }: { k: string; v: ReactNode; cls?: string }) {
  return (
    <div className="metric">
      <div className="k">{k}</div>
      <div className={`v ${cls ?? ""}`}>{v}</div>
    </div>
  );
}

export const STAT_LABELS: Record<string, string> = {
  shots: "Tiri totali",
  sot: "Tiri in porta",
  shots_off: "Tiri fuori",
  blocked: "Tiri respinti",
  shots_in_box: "Tiri in area",
  shots_out_box: "Tiri da fuori",
  corners: "Calci d'angolo",
  possession: "Possesso palla (%)",
  fouls: "Falli",
  yellow: "Cartellini gialli",
  red: "Cartellini rossi",
  saves: "Parate",
  offsides: "Fuorigioco",
  passes: "Passaggi",
  passes_acc: "Passaggi riusciti",
  xg: "Expected Goals (xG)",
  dangerous_attacks: "Attacchi pericolosi",
  attacks: "Attacchi",
  big_chances: "Big chances",
  xgot: "xGOT",
};

export const MARKET_NAMES: Record<string, string> = {
  total_goals: "Totale gol",
  btts: "Entrambe segnano",
  "1x2": "Esito 1X2",
  double_chance: "Doppia chance",
  dnb: "Draw No Bet",
  team_goals_home: "Gol squadra casa",
  team_goals_away: "Gol squadra ospite",
  next_goal: "Prossimo gol",
  goal_next_10: "Gol prossimi 10'",
  goal_window: "Gol in finestra 10'",
  ht_total_goals: "Totale gol 1° tempo",
  ht_1x2: "Esito 1° tempo",
  goal_2h: "Gol 2° tempo",
  correct_score: "Risultato esatto",
  total_corners: "Totale corner",
};

export const MODEL_NAMES: Record<string, string> = {
  goals_xg: "Hazard Poisson + xG",
  goals_stats: "Hazard Poisson (tiri, tiri in porta, corner)",
  goals_context: "Hazard Poisson (solo contesto)",
};
