import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const AXIS = { stroke: "var(--axis)", tick: { fill: "var(--text-muted)", fontSize: 11 }, tickLine: false };
const SERIES = ["var(--series-1)", "var(--series-2)", "var(--series-3)"];

function Tip({ active, payload, label, fmt, labelFmt }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="t">{labelFmt ? labelFmt(label) : label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey}>
          <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 2, background: p.color, marginRight: 6 }} />
          {p.name}: <b>{fmt ? fmt(p.value) : p.value}</b>
        </div>
      ))}
    </div>
  );
}

const shortTime = (v: any) => {
  if (v == null) return "";
  const d = typeof v === "number" ? new Date(v * 1000) : new Date(v);
  return d.toLocaleString("it-IT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
};

/** Single-series line over time. Title names the series, so no legend. */
export function TimeLine({ data, x, y, name, fmt, height = 220, area = false, color = "var(--series-1)" }: {
  data: any[]; x: string; y: string; name: string; fmt?: (v: number) => string; height?: number; area?: boolean; color?: string;
}) {
  if (!data?.length) return <div className="muted">Nessun dato disponibile</div>;
  const Chart: any = area ? AreaChart : LineChart;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <Chart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--grid)" vertical={false} />
        <XAxis dataKey={x} tickFormatter={shortTime} {...AXIS} minTickGap={40} />
        <YAxis {...AXIS} width={70} tickFormatter={fmt} domain={["auto", "auto"]} axisLine={false} />
        <Tooltip content={<Tip fmt={fmt} labelFmt={shortTime} />} cursor={{ stroke: "var(--text-muted)", strokeWidth: 1 }} />
        {area ? (
          <Area type="monotone" dataKey={y} name={name} stroke={color} strokeWidth={2} fill={color} fillOpacity={0.15}
                dot={false} activeDot={{ r: 4, stroke: "var(--surface-1)", strokeWidth: 2 }} isAnimationActive={false} />
        ) : (
          <Line type="monotone" dataKey={y} name={name} stroke={color} strokeWidth={2} dot={false}
                activeDot={{ r: 4, stroke: "var(--surface-1)", strokeWidth: 2 }} isAnimationActive={false} connectNulls />
        )}
      </Chart>
    </ResponsiveContainer>
  );
}

/** Up to 3 series on one axis (same unit), with legend + end labels. */
export function MultiLine({ data, x, series, fmt, height = 260 }: {
  data: any[]; x: string; series: { key: string; name: string }[]; fmt?: (v: number) => string; height?: number;
}) {
  if (!data?.length) return <div className="muted">Nessun dato disponibile</div>;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 60, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--grid)" vertical={false} />
        <XAxis dataKey={x} {...AXIS} minTickGap={40} />
        <YAxis {...AXIS} width={70} tickFormatter={fmt} axisLine={false} domain={["auto", "auto"]} />
        <Tooltip content={<Tip fmt={fmt} />} cursor={{ stroke: "var(--text-muted)", strokeWidth: 1 }} />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--text-secondary)" }} />
        {series.slice(0, 3).map((s, i) => (
          <Line key={s.key} type="monotone" dataKey={s.key} name={s.name} stroke={SERIES[i]} strokeWidth={2} dot={false}
                isAnimationActive={false} connectNulls
                label={(p: any) => (p.index === data.length - 1 ? (
                  <text x={p.x + 6} y={p.y} fill="var(--text-secondary)" fontSize={11} dominantBaseline="middle">{s.name}</text>
                ) : null) as any} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Signed bars (P/L): diverging blue (gain) / red (loss) + sign in tooltip. */
export function SignedBars({ data, x, y, name, fmt, height = 220 }: {
  data: any[]; x: string; y: string; name: string; fmt?: (v: number) => string; height?: number;
}) {
  if (!data?.length) return <div className="muted">Nessun dato disponibile</div>;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barCategoryGap={2}>
        <CartesianGrid stroke="var(--grid)" vertical={false} />
        <XAxis dataKey={x} {...AXIS} minTickGap={20} />
        <YAxis {...AXIS} width={70} tickFormatter={fmt} axisLine={false} />
        <ReferenceLine y={0} stroke="var(--axis)" />
        <Tooltip content={<Tip fmt={fmt} />} cursor={{ fill: "var(--surface-3)" }} />
        <Bar dataKey={y} name={name} isAnimationActive={false} maxBarSize={28}>
          {data.map((d, i) => {
            const pos = d[y] >= 0;
            return <Cell key={i} fill={pos ? "var(--gain)" : "var(--loss)"} radius={(pos ? [4, 4, 0, 0] : [0, 0, 4, 4]) as any} />;
          })}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Histogram of returns (fractions). */
export function Histogram({ values, bins = 20, height = 220 }: { values: number[]; bins?: number; height?: number }) {
  if (!values?.length) return <div className="muted">Nessuna operazione chiusa</div>;
  const lo = Math.max(-1, Math.min(...values));
  const hi = Math.max(...values);
  const w = (hi - lo) / bins || 0.01;
  const rows = Array.from({ length: bins }, (_, i) => ({ from: lo + i * w, count: 0 }));
  values.forEach((v) => {
    const idx = Math.min(bins - 1, Math.max(0, Math.floor((v - lo) / w)));
    rows[idx].count += 1;
  });
  const data = rows.map((r) => ({ bucket: `${(r.from * 100).toFixed(0)}%`, count: r.count, mid: r.from + w / 2 }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barCategoryGap={2}>
        <CartesianGrid stroke="var(--grid)" vertical={false} />
        <XAxis dataKey="bucket" {...AXIS} minTickGap={16} />
        <YAxis {...AXIS} width={40} allowDecimals={false} axisLine={false} />
        <Tooltip content={<Tip />} cursor={{ fill: "var(--surface-3)" }} />
        <Bar dataKey="count" name="Operazioni" isAnimationActive={false} radius={[4, 4, 0, 0] as any}>
          {data.map((d, i) => <Cell key={i} fill={d.mid >= 0 ? "var(--gain)" : "var(--loss)"} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Simple horizontal value bars (e.g. exposure per token). */
export function HBars({ data, fmt, height }: { data: { label: string; value: number }[]; fmt?: (v: number) => string; height?: number }) {
  if (!data?.length) return <div className="muted">Nessuna esposizione</div>;
  return (
    <ResponsiveContainer width="100%" height={height ?? Math.max(80, data.length * 36)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 40, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--grid)" horizontal={false} />
        <XAxis type="number" {...AXIS} tickFormatter={fmt} />
        <YAxis type="category" dataKey="label" {...AXIS} width={90} />
        <Tooltip content={<Tip fmt={fmt} />} cursor={{ fill: "var(--surface-3)" }} />
        <Bar dataKey="value" name="Valore" fill="var(--series-1)" radius={[0, 4, 4, 0] as any} isAnimationActive={false} maxBarSize={20} />
      </BarChart>
    </ResponsiveContainer>
  );
}
