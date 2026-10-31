import { useMemo, useRef, useState } from "react";

export interface Series {
  name: string;
  color: string; // CSS var reference, e.g. "var(--home)"
  points: { x: number; y: number }[];
  dashed?: boolean;
}

function niceTicks(min: number, max: number, count = 4): number[] {
  if (max <= min) return [min];
  const span = max - min;
  const step0 = span / count;
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const norm = step0 / mag;
  const step = (norm >= 5 ? 10 : norm >= 2 ? 5 : norm >= 1 ? 2 : 1) * mag;
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(Number(v.toFixed(10)));
  return out;
}

/** Multi-series line chart with a snapping crosshair + one tooltip listing every series. */
export function LineChart({
  series,
  height = 220,
  xLabel,
  yFormat = (v: number) => String(v),
  xFormat = (v: number) => String(v),
  step = false,
}: {
  series: Series[];
  height?: number;
  xLabel?: string;
  yFormat?: (v: number) => string;
  xFormat?: (v: number) => string;
  step?: boolean;
}) {
  const width = 640;
  const m = { l: 44, r: 16, t: 10, b: 30 };
  const ref = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const all = series.flatMap((s) => s.points);
  const xs = useMemo(() => Array.from(new Set(all.map((p) => p.x))).sort((a, b) => a - b), [all]);
  if (all.length === 0) return <div className="empty small">Nessun dato da mostrare</div>;
  const xmin = Math.min(...xs);
  const xmax = Math.max(...xs, xmin + 1);
  const ymin = Math.min(0, ...all.map((p) => p.y));
  const ymax = Math.max(...all.map((p) => p.y), ymin + 1);
  const sx = (x: number) => m.l + ((x - xmin) / (xmax - xmin)) * (width - m.l - m.r);
  const sy = (y: number) => height - m.b - ((y - ymin) / (ymax - ymin)) * (height - m.t - m.b);
  const path = (pts: { x: number; y: number }[]) =>
    pts
      .map((p, i) => {
        if (i === 0 || !step) return `${i ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`;
        return `H${sx(p.x).toFixed(1)}V${sy(p.y).toFixed(1)}`;
      })
      .join("");
  const yt = niceTicks(ymin, ymax);
  const xt = niceTicks(xmin, xmax, 6);

  const onMove = (e: React.PointerEvent) => {
    const svg = ref.current;
    if (!svg) return;
    const r = svg.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * width;
    let best = xs[0];
    for (const v of xs) if (Math.abs(sx(v) - x) < Math.abs(sx(best) - x)) best = v;
    setHover(best);
  };
  const valueAt = (s: Series, x: number) => {
    let v: number | null = null;
    for (const p of s.points) if (p.x <= x) v = p.y;
    return v;
  };

  return (
    <div className="chart">
      {series.length > 1 && (
        <div className="legend">
          {series.map((s) => (
            <span key={s.name}>
              <span className={`key ${s.dashed ? "dashed" : ""}`} style={{ background: s.color }} />
              {s.name}
            </span>
          ))}
        </div>
      )}
      <svg
        ref={ref}
        viewBox={`0 0 ${width} ${height}`}
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
        role="img"
        aria-label={series.map((s) => s.name).join(", ")}
      >
        {yt.map((t) => (
          <g key={t}>
            <line x1={m.l} x2={width - m.r} y1={sy(t)} y2={sy(t)} stroke="var(--grid)" strokeWidth={1} />
            <text x={m.l - 6} y={sy(t) + 4} fontSize={11} textAnchor="end" fill="var(--muted)">
              {yFormat(t)}
            </text>
          </g>
        ))}
        <line x1={m.l} x2={width - m.r} y1={sy(ymin)} y2={sy(ymin)} stroke="var(--axis)" strokeWidth={1} />
        {xt.map((t) => (
          <text key={t} x={sx(t)} y={height - m.b + 16} fontSize={11} textAnchor="middle" fill="var(--muted)">
            {xFormat(t)}
          </text>
        ))}
        {xLabel && (
          <text x={width - m.r} y={height - 2} fontSize={11} textAnchor="end" fill="var(--muted)">
            {xLabel}
          </text>
        )}
        {series.map((s) => (
          <path
            key={s.name}
            d={path(s.points)}
            fill="none"
            stroke={s.color}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
            strokeDasharray={s.dashed ? "4 3" : undefined}
          />
        ))}
        {series.map((s) => {
          const last = s.points[s.points.length - 1];
          if (!last) return null;
          return <circle key={s.name} cx={sx(last.x)} cy={sy(last.y)} r={4} fill={s.color} stroke="var(--surface)" strokeWidth={2} />;
        })}
        {hover !== null && (
          <line x1={sx(hover)} x2={sx(hover)} y1={m.t} y2={height - m.b} stroke="var(--axis)" strokeWidth={1} />
        )}
        <rect x={m.l} y={m.t} width={width - m.l - m.r} height={height - m.t - m.b} fill="transparent" />
      </svg>
      {hover !== null && (
        <div
          className="tooltip"
          style={{ left: `${(sx(hover) / width) * 100}%`, top: 8, transform: sx(hover) > width * 0.6 ? "translateX(-105%)" : "translateX(8px)" }}
        >
          <div className="muted">{xFormat(hover)}</div>
          {series.map((s) => {
            const v = valueAt(s, hover);
            return (
              <div className="row" key={s.name}>
                <span className="lk" style={{ background: s.color }} />
                <strong>{v === null ? "—" : yFormat(v)}</strong>
                <span className="muted">{s.name}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export interface CalSeries {
  name: string;
  color: string;
  bins: { p_mean: number; obs: number; n: number; se?: number }[];
}

/** Reliability diagram: predicted probability (x) vs observed frequency (y), diagonal = perfect calibration. */
export function CalibrationChart({ series, height = 340 }: { series: CalSeries[]; height?: number }) {
  const width = 480;
  const m = { l: 40, r: 12, t: 10, b: 32 };
  const [tip, setTip] = useState<{ x: number; y: number; s: string; b: CalSeries["bins"][number] } | null>(null);
  const sx = (x: number) => m.l + x * (width - m.l - m.r);
  const sy = (y: number) => height - m.b - y * (height - m.t - m.b);
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  const total = series.reduce((a, s) => a + s.bins.length, 0);
  if (total === 0) return <div className="empty small">Nessun dato di calibrazione disponibile</div>;
  return (
    <div className="chart" style={{ maxWidth: 520 }}>
      <div className="legend">
        {series.map((s) => (
          <span key={s.name}>
            <span className="key" style={{ background: s.color }} />
            {s.name}
          </span>
        ))}
        <span>
          <span className="key dashed" />
          calibrazione perfetta
        </span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Diagramma di calibrazione">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={m.l} x2={width - m.r} y1={sy(t)} y2={sy(t)} stroke="var(--grid)" />
            <text x={m.l - 6} y={sy(t) + 4} fontSize={10} textAnchor="end" fill="var(--muted)">
              {Math.round(t * 100)}%
            </text>
            <text x={sx(t)} y={height - m.b + 14} fontSize={10} textAnchor="middle" fill="var(--muted)">
              {Math.round(t * 100)}%
            </text>
          </g>
        ))}
        <text x={width - m.r} y={height - 4} fontSize={10} textAnchor="end" fill="var(--muted)">
          probabilità stimata
        </text>
        <line x1={sx(0)} y1={sy(0)} x2={sx(1)} y2={sy(1)} stroke="var(--muted)" strokeDasharray="4 3" strokeWidth={1} />
        {series.map((s) => (
          <g key={s.name}>
            <path
              d={s.bins.map((b, i) => `${i ? "L" : "M"}${sx(b.p_mean).toFixed(1)},${sy(b.obs).toFixed(1)}`).join("")}
              fill="none"
              stroke={s.color}
              strokeWidth={2}
              strokeLinejoin="round"
            />
            {s.bins.map((b) => (
              <g key={b.p_mean}>
                <circle cx={sx(b.p_mean)} cy={sy(b.obs)} r={4} fill={s.color} stroke="var(--surface)" strokeWidth={2} />
                <circle
                  cx={sx(b.p_mean)}
                  cy={sy(b.obs)}
                  r={12}
                  fill="transparent"
                  onPointerEnter={() => setTip({ x: sx(b.p_mean), y: sy(b.obs), s: s.name, b })}
                  onPointerLeave={() => setTip(null)}
                />
              </g>
            ))}
          </g>
        ))}
      </svg>
      {tip && (
        <div
          className="tooltip"
          style={{ left: `${(tip.x / width) * 100}%`, top: `${(tip.y / height) * 100}%`, transform: "translate(10px, -50%)" }}
        >
          <div className="row">
            <strong>{(tip.b.obs * 100).toFixed(1)}%</strong>
            <span className="muted">osservato</span>
          </div>
          <div className="row">
            <strong>{(tip.b.p_mean * 100).toFixed(1)}%</strong>
            <span className="muted">stimato</span>
          </div>
          <div className="muted">
            {tip.s} · n = {tip.b.n}
          </div>
        </div>
      )}
    </div>
  );
}

/** Probability interval (10-90%) with point estimate and the implied probability marker. */
export function ProbRange({ low, high, p, implied }: { low: number; high: number; p: number; implied: number }) {
  const lo = Math.min(low, implied, p) - 0.05;
  const hi = Math.max(high, implied, p) + 0.05;
  const a = Math.max(0, lo);
  const b = Math.min(1, hi);
  const pos = (x: number) => `${((x - a) / (b - a)) * 100}%`;
  return (
    <div
      className="range"
      title={`stima ${(p * 100).toFixed(1)}% · intervallo ${(low * 100).toFixed(1)}–${(high * 100).toFixed(1)}% · implicita ${(implied * 100).toFixed(1)}%`}
    >
      <div className="track" />
      <div className="band" style={{ left: pos(low), width: `calc(${pos(high)} - ${pos(low)})` }} />
      <div className="imp" style={{ left: pos(implied) }} />
      <div className="pt" style={{ left: pos(p) }} />
    </div>
  );
}
