// Charts as inline SVG.
//
// No charting library on purpose. Recharts or Chart.js would add ~150 kB and,
// more importantly, third-party code inside the demo that demo_proof.py
// certifies runs with every socket blocked. These are a few dozen lines of
// arithmetic and they inherit the theme colours for free.

import { compactMoney, num } from "../api.js";

// Ordered tonal ramp rather than a rainbow. Rainbow categorical palettes
// imply the categories are unrelated; these are slices of one machine, so a
// controlled ramp reads as a breakdown instead of a legend.
//
// The steps are solved for even PERCEIVED separation, not picked by eye: each
// one targets a luminance on a geometric progression, so every adjacent pair
// sits at 1.36:1 — the earlier hand-mixed version drifted to 1.01:1 in the
// middle, where two segments were the same value in different hues and the
// donut lost its boundaries. Hue rotates aqua → periwinkle → lavender across
// the ramp, so it stays inside the palette.
const RING = ["#12292b", "#233e4e", "#394f77", "#555baa",
              "#776fb3", "#9387bc", "#aea1c8", "#c9bfd8"];

/* Horizontal bars — cost comparison, efficiency. ---------------------------- */
export function BarChart({ rows, format = compactMoney, accent = "var(--accent)",
                           valueKey = "value" }) {
  if (!rows?.length) return <div className="empty">no data</div>;
  const max = Math.max(...rows.map((r) => Math.abs(r[valueKey] || 0))) || 1;

  return (
    <div className="chart-rows">
      {rows.map((r, i) => {
        const pct = (Math.abs(r[valueKey] || 0) / max) * 100;
        const baseline = r.is_baseline;
        return (
          <div className="chart-row" key={i}>
            <span className="chart-lbl" title={r.label}>
              {r.label}
            </span>
            <div className="chart-track">
              <i
                style={{
                  width: `${pct}%`,
                  background: baseline ? "#6f6e68" : accent,
                  animationDelay: `${i * 70}ms`,
                }}
              />
            </div>
            <span className="chart-val">{format(r[valueKey])}</span>
          </div>
        );
      })}
    </div>
  );
}

/* Donut — cost split by subsystem. ------------------------------------------ */
export function Donut({ rows }) {
  if (!rows?.length) return <div className="empty">no data</div>;

  const total = rows.reduce((sum, r) => sum + (r.value || 0), 0) || 1;
  const R = 54;
  const C = 2 * Math.PI * R;
  let offset = 0;

  const segments = rows.map((r, i) => {
    const frac = (r.value || 0) / total;
    const seg = {
      key: i,
      label: r.label,
      name: r.name,
      value: r.value,
      pct: frac * 100,
      colour: RING[i % RING.length],
      dash: `${frac * C} ${C - frac * C}`,
      offset: -offset * C,
    };
    offset += frac;
    return seg;
  });

  return (
    <div className="donut-wrap">
      <svg viewBox="0 0 140 140" className="donut">
        <g transform="translate(70,70) rotate(-90)">
          {segments.map((s) => (
            <circle
              key={s.key}
              r={R}
              fill="none"
              stroke={s.colour}
              strokeWidth="17"
              strokeDasharray={s.dash}
              strokeDashoffset={s.offset}
              opacity="0.92"
            />
          ))}
        </g>
        <text
          x="70"
          y="66"
          textAnchor="middle"
          fill="#ecebe6"
          style={{ font: "600 15px var(--font-mono)" }}
        >
          {compactMoney(total)}
        </text>
        <text
          x="70"
          y="82"
          textAnchor="middle"
          fill="#6f6e68"
          style={{ font: "500 7px var(--font-mono)", letterSpacing: "0.14em" }}
        >
          TOTAL
        </text>
      </svg>

      <div className="legend">
        {segments.map((s) => (
          <div className="legend-row" key={s.key} title={s.name}>
            <i style={{ background: s.colour }} />
            <span className="legend-lbl">{s.label}</span>
            <span className="legend-val">{num(s.pct, 1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* Timeline — years to build, as a gantt-ish rail. --------------------------- */
export function Timeline({ rows }) {
  if (!rows?.length) return <div className="empty">no data</div>;
  const max = Math.max(...rows.map((r) => r.years || 0)) || 1;

  return (
    <div className="chart-rows">
      {rows.map((r, i) => (
        <div className="chart-row" key={i}>
          <span className="chart-lbl">{r.label}</span>
          <div className="chart-track">
            <i
              style={{
                width: `${((r.years || 0) / max) * 100}%`,
                background: "var(--accent)",
                animationDelay: `${i * 70}ms`,
              }}
            />
          </div>
          <span className="chart-val">{num(r.years, 1)} yr</span>
        </div>
      ))}
    </div>
  );
}

/* Scatter — the cost/efficiency trade-off frontier. -------------------------- */
export function Frontier({ points }) {
  if (!points?.length) return <div className="empty">no frontier</div>;

  const W = 320;
  const H = 190;
  const pad = 30;

  const xs = points.map((p) => p.cost_usd);
  const ys = points.map((p) => p.efficiency_pct);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yMin = Math.min(...ys);
  const yMax = Math.max(...ys);

  const px = (v) => pad + ((v - xMin) / (xMax - xMin || 1)) * (W - pad * 1.3);
  const py = (v) => H - pad - ((v - yMin) / (yMax - yMin || 1)) * (H - pad * 1.5);

  const path = points
    .map((p, i) => `${i ? "L" : "M"} ${px(p.cost_usd)} ${py(p.efficiency_pct)}`)
    .join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="scatter" style={{ color: "var(--accent)" }}>
      {[0, 0.5, 1].map((f) => (
        <line
          key={f}
          x1={pad}
          x2={W - 8}
          y1={py(yMin + f * (yMax - yMin))}
          y2={py(yMin + f * (yMax - yMin))}
          stroke="#2a2d34"
          strokeWidth="1"
        />
      ))}

      <path d={path} fill="none" stroke="currentColor" strokeWidth="2" />

      {points.map((p, i) => (
        <circle
          key={i}
          cx={px(p.cost_usd)}
          cy={py(p.efficiency_pct)}
          r="3"
          fill="currentColor"
          opacity="0.85"
        >
          <title>
            {compactMoney(p.cost_usd)} · {num(p.efficiency_pct, 1)}% ·{" "}
            {num(p.timeline_years, 1)} yr
          </title>
        </circle>
      ))}

      <text x={pad} y={H - 8} fill="#6f6e68" style={{ font: "500 8px var(--font-mono)" }}>
        {compactMoney(xMin)}
      </text>
      <text x={W - 8} y={H - 8} textAnchor="end" fill="#6f6e68" style={{ font: "500 8px var(--font-mono)" }}>
        {compactMoney(xMax)}
      </text>
      <text x={4} y={py(yMax)} fill="#6f6e68" style={{ font: "500 8px var(--font-mono)" }}>
        {num(yMax, 0)}%
      </text>
      <text x={4} y={py(yMin)} fill="#6f6e68" style={{ font: "500 8px var(--font-mono)" }}>
        {num(yMin, 0)}%
      </text>
    </svg>
  );
}

/* Sparkline — a value's shape in the space of a word. -------------------- */
export function Spark({ values, width = 74, height = 20 }) {
  if (!values?.length || values.length < 2) return null;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = width / (values.length - 1);

  const points = values
    .map((v, i) => `${i * step},${height - ((v - min) / span) * height}`)
    .join(" ");

  return (
    <svg className="spark" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <polyline points={points} fill="none" stroke="currentColor"
                strokeWidth="1.25" vectorEffect="non-scaling-stroke" />
      <circle cx={(values.length - 1) * step}
              cy={height - ((values[values.length - 1] - min) / span) * height}
              r="1.8" fill="currentColor" />
    </svg>
  );
}

/* Micro-bar — an inline magnitude cue inside a table cell. --------------- */
export function Micro({ pct, tone = "" }) {
  const w = Math.max(0, Math.min(100, Number(pct) || 0));
  return (
    <span className={`micro ${tone}`}>
      <i style={{ width: `${w}%` }} />
    </span>
  );
}
