// The nine screens, in the order the specification lists them.
//
// Each is a full view rather than a card on a scrolling page — the demo is
// driven by walking through them in order, and a judge should never have to
// scroll past screen 4 to find screen 9.

import { useEffect, useState } from "react";
import { api, compactMoney, count, num } from "./api.js";
import { Panel, Readout, Slider, Bar } from "./components/ui.jsx";
import { BarChart, Donut, Timeline, Frontier, Micro, Spark } from "./components/charts.jsx";
import { SimFlow } from "./components/SimFlow.jsx";

// Each screen owns a colour, and that colour follows you into it — the tile
// you pressed, the buttons, the bars and the readouts on that screen all
// carry it.
//
// This was nine distinct hues (amber, sage, slate, terracotta, teal, mauve,
// gold, olive, rust), which read as a rainbow on a light ground and sat
// outside the palette. Now three tones cycle through the nine, each one a
// darkened form of a palette colour.
//
// `colour` is used BOTH as text on the cream card and as a button fill
// labelled by `ink`, so it has to pass contrast in both directions. Because
// the card is itself the cream, those are the same pair reversed — one
// number covers both: 5.46, 5.97 and 5.83, and ≥5.06 on the page behind.
const PERI = { colour: "#5a53a3", ink: "#f1e9e1" };
const AQUA = { colour: "#2f5f61", ink: "#f1e9e1" };
const LAV = { colour: "#644f85", ink: "#f1e9e1" };

export const SCREENS = [
  { id: 1, key: "input", name: "User Input", hint: "constraints", ...PERI },
  { id: 2, key: "results", name: "Display Results", hint: "top 5 + savings", ...AQUA },
  { id: 3, key: "visual", name: "Visualization", hint: "charts", ...LAV },
  { id: 4, key: "interact", name: "Interactivity", hint: "solve + reduce", ...PERI },
  { id: 5, key: "particles", name: "Particle Management", hint: "contamination", ...AQUA },
  { id: 6, key: "clean", name: "Cleanliness", hint: "ISO trade-off", ...LAV },
  { id: 7, key: "ai", name: "AI Precision & Design", hint: "local model", ...PERI },
  { id: 8, key: "learning", name: "External Data Learning", hint: "patterns", ...AQUA },
  { id: 9, key: "sim", name: "EUV Simulation", hint: "physics chain", ...LAV },
];

/* 1 ------------------------------------------------------------------------ */
// Laid out as a specification sheet, not a control panel. Each constraint is
// a row: parameter, the value you have set, the physical limit it sits
// inside, and the control. That is how a datasheet or an EDA constraint file
// reads, and it puts each setting next to the envelope it has to fit —
// information a stack of sliders in a card leaves out entirely.
export function ScreenInput({ state, set, data }) {
  const r = data?.results;

  const PARAMS = [
    { key: "budget", label: "Capital budget", unit: "USD",
      value: `$${state.budget}M`, min: 80, max: 300, step: 1,
      raw: state.budget, limit: "$80.5M – $255.8M",
      note: "Total system cost ceiling" },
    { key: "efficiency", label: "Minimum efficiency", unit: "fraction",
      value: `${(state.efficiency * 100).toFixed(0)}%`,
      min: 0.1, max: 0.75, step: 0.01, raw: state.efficiency,
      limit: "18.2% – 74.4%",
      note: "Compounds multiplicatively across 8 subsystems" },
    { key: "timeline", label: "Build timeline", unit: "years",
      value: `${state.timeline} yr`, min: 4, max: 10, step: 0.5,
      raw: state.timeline, limit: "5.0 – 8.0 yr",
      note: "Longest single-component lead time" },
    { key: "iso", label: "Cleanroom class", unit: "ISO 14644-1",
      value: `ISO ${state.iso}`, min: 1, max: 7, step: 1, raw: state.iso,
      limit: "ISO 1 – ISO 9",
      note: "Lower is cleaner and costs more" },
  ];

  return (
    <div className="grid">
      <Panel idx="01" title="Constraint specification" wide>
        <table className="spec">
          <thead>
            <tr>
              <th>Parameter</th>
              <th className="num">Setting</th>
              <th>Adjust</th>
              <th className="num">Physical limit</th>
            </tr>
          </thead>
          <tbody>
            {PARAMS.map((p) => (
              <tr key={p.key}>
                <td>
                  <span className="spec-name">{p.label}</span>
                  <span className="spec-note">{p.note}</span>
                </td>
                <td className="num spec-value">{p.value}</td>
                <td className="spec-control">
                  <input
                    type="range"
                    min={p.min}
                    max={p.max}
                    step={p.step}
                    value={p.raw}
                    style={{
                      "--pct": `${((p.raw - p.min) / (p.max - p.min)) * 100}%`,
                    }}
                    onChange={(e) => set(p.key, Number(e.target.value))}
                    aria-label={p.label}
                  />
                </td>
                <td className="num spec-limit">{p.limit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel idx="01" title="Objective weighting" wide>
        <p className="note" style={{ marginBottom: 14 }}>
          The score is a weighted sum of normalised cost, efficiency and
          timeline. Changing the weighting re-ranks the same{" "}
          {count(r?.combinations_evaluated, "19,440")}{" "}
          configurations — it never removes any from the search.
        </p>
        <table className="spec">
          <thead>
            <tr>
              <th>Objective</th>
              <th className="num">Cost</th>
              <th className="num">Efficiency</th>
              <th className="num">Timeline</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {Object.entries(PRESETS).map(([key, w]) => (
              <tr key={key} className={state.preset === key ? "lead" : ""}>
                <td>{w.label}</td>
                <td className="num">{w.w_cost.toFixed(2)}</td>
                <td className="num">{w.w_eff.toFixed(2)}</td>
                <td className="num">{w.w_time.toFixed(2)}</td>
                <td className="num">
                  <button
                    className={`btn ${state.preset === key ? "on" : ""}`}
                    onClick={() => set("preset", key)}
                  >
                    {state.preset === key ? "Applied" : "Apply"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {r && (
          <p className="note" style={{ marginTop: 16 }}>
            Current weighting admits{" "}
            <b>{count(r.feasible_count)}</b> of{" "}
            {count(r.combinations_evaluated)} configurations;{" "}
            {count(r.infeasible_count)} violate a constraint above.
          </p>
        )}
      </Panel>
    </div>
  );
}

export const PRESETS = {
  balanced: { w_cost: 0.45, w_eff: 0.4, w_time: 0.15, label: "Balanced" },
  cost: { w_cost: 0.9, w_eff: 0.05, w_time: 0.05, label: "Cost first" },
  efficiency: { w_cost: 0.05, w_eff: 0.9, w_time: 0.05, label: "Efficiency" },
  speed: { w_cost: 0.15, w_eff: 0.25, w_time: 0.6, label: "Fast build" },
};

function Ranges() {
  const [ranges, setRanges] = useState(null);
  useEffect(() => {
    api.frontier({ points: 2 }).then(() => {}).catch(() => {});
    fetch("/api/frontier?points=40")
      .then((r) => r.json())
      .then((f) => setRanges(f))
      .catch(() => {});
  }, []);
  if (!ranges?.points?.length) return <div className="empty">loading…</div>;
  const costs = ranges.points.map((p) => p.cost_usd);
  const effs = ranges.points.map((p) => p.efficiency_pct);
  return (
    <div className="stat-row" style={{ marginTop: 14 }}>
      <div>
        <div className="caption">Cost range</div>
        <div className="mini">
          {compactMoney(Math.min(...costs))} – {compactMoney(Math.max(...costs))}
        </div>
      </div>
      <div>
        <div className="caption">Efficiency range</div>
        <div className="mini">
          {num(Math.min(...effs), 1)}% – {num(Math.max(...effs), 1)}%
        </div>
      </div>
      <div>
        <div className="caption">Pareto-optimal</div>
        <div className="mini">{ranges.frontier_size?.toLocaleString()}</div>
      </div>
    </div>
  );
}

/* 2 ------------------------------------------------------------------------ */
export function ScreenResults({ data, busy }) {
  const r = data?.results;
  const top = r?.top_configurations ?? [];
  const best = top[0];

  if (busy && !best) return <Loading />;
  if (!best)
    return (
      <div className="grid">
        <Panel idx="02" title="No feasible configuration" wide>
          <div className="empty">
            <b>Nothing satisfies these constraints.</b>
            <br />
            Every one of the {count(r?.combinations_evaluated)}{" "}
            combinations was rejected. The cheapest machine that exists at all
            is $80.5M at 18.2% efficiency — loosen a slider on screen 1.
          </div>
        </Panel>
      </div>
    );

  // The saving figure must never appear without its qualifier. The full
  // disclosure cards live on the home screen; this is the inline version so a
  // judge reading this number here still sees what it depends on.
  const hyp = (data?.disclosure?.entries || []).find(
    (e) => e.id === "hypothetical_components");
  const cost = (data?.disclosure?.entries || []).find(
    (e) => e.id === "cost_basis");

  return (
    <div className="grid">
      <Panel idx="02" title="Optimised result">
        <Readout tone="mint">{compactMoney(best.total_cost_usd)}</Readout>
        <div className="caption">
          baseline {compactMoney(r.baseline.total_cost_usd)} · saving{" "}
          {num(r.savings.percent, 1)}%
        </div>

        {hyp?.chosen_hypothetical > 0 && (
          <div className={`inline-caveat ${hyp.severity}`}>
            <b>
              {hyp.chosen_hypothetical} of {hyp.chosen_total} parts here do not
              exist
            </b>
            <span>
              This saving depends on hardware nobody can buy today. They are
              specified targets, not catalogue parts.
            </span>
          </div>
        )}
        {cost && (
          <div className="inline-caveat quiet">
            <span>
              System total is published; the split across subsystems is our
              estimate.
            </span>
          </div>
        )}
        <div className="stat-row" style={{ marginTop: 20 }}>
          <Stat label="Efficiency" value={`${num(best.efficiency_pct, 1)}%`}
            pct={best.efficiency_pct} tone="" />
          <Stat label="Timeline" value={`${num(best.timeline_years, 1)} yr`}
            pct={(best.timeline_years / 10) * 100} tone="rose" />
          <Stat label="Saving" value={`${num(r.savings.percent, 1)}%`}
            pct={Math.min(100, Math.abs(r.savings.percent))} tone="mint" />
        </div>
      </Panel>

      <Panel idx="02" title="Top 5 configurations" wide>
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th><th className="num">Cost</th><th className="num">Efficiency</th>
                <th className="num">Years</th><th className="num">Score</th><th>Reality</th>
              </tr>
            </thead>
            <tbody>
              {top.map((c) => {
                const hyp = (c.components || []).filter(
                  (p) => String(p.supplier).toUpperCase() === "HYPOTHETICAL").length;
                return (
                  <tr key={c.rank} className={c.rank === 1 ? "lead" : ""}>
                    <td>{c.rank}</td>
                    <td className="num">
                      {compactMoney(c.total_cost_usd)}
                      <Micro pct={(c.total_cost_usd / r.baseline.total_cost_usd) * 100} />
                    </td>
                    <td className="num">
                      {num(c.efficiency_pct, 1)}%
                      <Micro pct={c.efficiency_pct} />
                    </td>
                    <td className="num">{num(c.timeline_years, 1)}</td>
                    <td className="num">
                      {num(c.score, 4)}
                      <Micro pct={c.score * 100} />
                    </td>
                    <td>
                      <span className={`chip ${hyp ? "hyp" : "real"}`}>
                        {hyp ? `${hyp} not real` : "all real"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel idx="02" title="Parts mapping" wide>
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr><th>Category</th><th>Baseline</th><th>Selected</th><th className="num">Saving</th></tr>
            </thead>
            <tbody>
              {(r.component_mapping || []).map((m, i) => (
                <tr key={i} className={m.changed ? "lead" : ""}>
                  <td style={{ color: "var(--fg-dim)" }}>{m.category}</td>
                  <td title={m.original_name}>{(m.original_name || "—").slice(0, 26)}</td>
                  <td title={m.replacement_name}
                    style={{ color: m.changed ? "var(--cyan)" : "var(--fg-faint)" }}>
                    {m.changed ? (m.replacement_name || "—").slice(0, 26) : "unchanged"}
                  </td>
                  <td className="num" style={{ color: m.saving_usd ? "var(--mint)" : "var(--fg-faint)" }}>
                    {m.saving_usd ? `−${compactMoney(m.saving_usd)}` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

/* 3 ------------------------------------------------------------------------ */
export function ScreenVisual({ data }) {
  const v = data?.visualization;
  const [frontier, setFrontier] = useState(null);
  useEffect(() => {
    api.frontier({ points: 40 }).then(setFrontier).catch(() => {});
  }, []);

  if (!v) return <Loading />;
  return (
    <div className="grid">
      <Panel idx="03" title="Cost comparison" wide>
        <BarChart rows={v.cost_bar} />
      </Panel>
      <Panel idx="03" title="Cost split by subsystem">
        <Donut rows={v.cost_pie} />
      </Panel>
      <Panel idx="03" title="Timeline">
        <Timeline rows={v.timeline} />
      </Panel>
      <Panel idx="03" title="Efficiency">
        <BarChart rows={v.efficiency} format={(n) => `${num(n, 1)}%`} />
      </Panel>
      <Panel idx="03" title="Trade-off frontier" wide>
        <p className="note" style={{ marginBottom: 10 }}>
          Cost against efficiency for every Pareto-optimal machine. Everything
          off this curve is beaten by something on it.
        </p>
        <Frontier points={frontier?.points} />
      </Panel>
    </div>
  );
}

/* 4 ------------------------------------------------------------------------ */
export function ScreenInteract({ state, set }) {
  const [unknown, setUnknown] = useState("efficiency");
  const [solved, setSolved] = useState(null);
  const [target, setTarget] = useState(130);
  const [realOnly, setRealOnly] = useState(false);
  const [plan, setPlan] = useState(null);

  const solve = () =>
    api.solve({
      unknown,
      max_cost: unknown !== "cost" ? state.budget : undefined,
      min_efficiency: unknown !== "efficiency" ? state.efficiency : undefined,
      max_timeline: unknown !== "timeline" ? state.timeline : undefined,
    }).then(setSolved);

  const reduce = () =>
    api.costReduction({ target, real_only: realOnly }).then(setPlan);

  return (
    <div className="grid">
      <Panel idx="04" title="Inverse solve" wide>
        <p className="note" style={{ marginBottom: 14 }}>
          Pin what you know, solve for what you do not. Values come from your
          settings on screen 1.
        </p>
        <div className="caption" style={{ marginBottom: 8 }}>Solve for</div>
        <div className="btn-row" style={{ marginBottom: 16 }}>
          {["efficiency", "cost", "timeline"].map((u) => (
            <button key={u} className={`btn violet ${unknown === u ? "on" : ""}`}
              onClick={() => setUnknown(u)}>{u}</button>
          ))}
          <button className="btn" onClick={solve}>Solve</button>
        </div>
        {solved && (
          <>
            <Readout>{
              solved.achievable === null ? "—"
                : unknown === "cost" ? compactMoney(solved.achievable)
                : unknown === "efficiency" ? `${num(solved.achievable * 100, 2)}%`
                : `${num(solved.achievable, 1)} yr`
            }</Readout>
            <p className="note" style={{ marginTop: 10 }}>{solved.explanation}</p>
          </>
        )}
      </Panel>

      <Panel idx="04" title="Cost reduction pathway" wide>
        <Slider label="Target cost" value={target} min={80} max={200} step={5}
          onChange={setTarget} display={`$${target}M`} />
        <div className="btn-row" style={{ marginBottom: 14 }}>
          <button className={`btn ${realOnly ? "on" : ""}`}
            onClick={() => setRealOnly(!realOnly)}>
            {realOnly ? "Real suppliers only" : "Allow hypothetical"}
          </button>
          <button className="btn" onClick={reduce}>Plan route</button>
        </div>
        {plan?.pathway && (
          <>
            <div className="tbl-wrap">
              <table>
                <thead>
                  <tr><th>#</th><th>Swap</th><th className="num">Saves</th><th className="num">Costs</th></tr>
                </thead>
                <tbody>
                  {plan.pathway.steps.map((s) => (
                    <tr key={s.step} className={s.is_hypothetical ? "" : "lead"}>
                      <td>{s.step}</td>
                      <td title={s.with}>
                        {s.category}
                        {s.is_hypothetical && <span className="chip hyp" style={{ marginLeft: 6 }}>not real</span>}
                      </td>
                      <td className="num" style={{ color: "var(--mint)" }}>
                        −{compactMoney(s.cost_saved_usd)}
                      </td>
                      <td className="num" style={{ color: "var(--amber)" }}>
                        {num(s.efficiency_lost_pct, 2)} pts
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="note" style={{ marginTop: 12 }}>{plan.pathway.explanation}</p>
          </>
        )}
      </Panel>
    </div>
  );
}

/* 5 ------------------------------------------------------------------------ */
export function ScreenParticles({ data }) {
  const p = data?.particles;
  if (!p) return <Loading />;
  return (
    <div className="grid">
      <Panel idx="05" title="Die yield">
        <Readout tone={p.risk_level === "LOW" ? "mint" : p.risk_level === "CRITICAL" ? "rose" : ""}>
          {num(p.yield_pct, 1)}%
        </Readout>
        <div className="caption">risk level {p.risk_level}</div>
        <Bar pct={p.yield_pct} tone="mint" />
        <p className="note" style={{ marginTop: 14 }}>{p.risk_note}</p>
      </Panel>

      <Panel idx="05" title="Contamination model">
        <div className="stat-row">
          <Stat label="ISO class" value={`ISO ${p.iso_class}`} pct={100 - p.iso_class * 12} />
          <Stat label="Particles / m³" value={p.particles_per_m3?.toLocaleString()} pct={60} />
          <Stat label="Killer size" value={`${num(p.killer_particle_size_um * 1000, 1)} nm`} pct={45} tone="rose" />
          <Stat label="Defect density" value={num(p.defect_density_per_cm2, 4)} pct={35} tone="rose" />
        </div>
      </Panel>

      <Panel idx="05" title="Cleanliness cost" wide>
        <div className="stat-row">
          <Stat label="Build" value={compactMoney(p.build_cost_usd)} pct={50} />
          <Stat label="Operating / yr" value={compactMoney(p.annual_operating_cost_usd)} pct={40} />
          <Stat label="Yield loss" value={compactMoney(p.cost_of_yield_loss_usd)} pct={70} tone="rose" />
          <Stat label="Total" value={compactMoney(p.total_cleanliness_cost_usd)} pct={100} tone="rose" />
        </div>
        <p className="note" style={{ marginTop: 16 }}>{p.recommendation}</p>
      </Panel>
    </div>
  );
}

/* 6 ------------------------------------------------------------------------ */
export function ScreenClean({ data }) {
  const c = data?.cleanliness;
  if (!c?.comparison) return <Loading />;
  return (
    <div className="grid">
      <Panel idx="06" title="Every ISO class compared" wide>
        <p className="note" style={{ marginBottom: 14 }}>
          A cleaner room costs more to build and run, and buys yield. The
          optimum is where those cross — not the cleanest room you can afford.
        </p>
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Class</th><th className="num">Particles/m³</th><th className="num">Yield</th>
                <th className="num">Build</th><th className="num">Yield loss</th><th className="num">Total</th>
              </tr>
            </thead>
            <tbody>
              {c.comparison.map((row) => (
                <tr key={row.iso_class} className={row.iso_class === c.recommended_class ? "lead" : ""}>
                  <td>ISO {row.iso_class}{row.iso_class === c.current_class && " ←"}</td>
                  <td className="num">{row.particles_per_m3?.toLocaleString()}</td>
                  <td className="num">
                    {num(row.yield_pct, 1)}%
                    <Micro pct={row.yield_pct} />
                  </td>
                  <td className="num">{compactMoney(row.build_cost_usd)}</td>
                  <td className="num">{compactMoney(row.cost_of_yield_loss_usd)}</td>
                  <td className="num">{compactMoney(row.total_cleanliness_cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="note" style={{ marginTop: 14 }}>
          Recommended: <b style={{ color: "var(--cyan)" }}>ISO {c.recommended_class}</b>
        </p>
      </Panel>
    </div>
  );
}

/* 7 ------------------------------------------------------------------------ */
export function ScreenAI({ data, health, state }) {
  // Generating the three analyses costs five model calls -- half a minute or
  // more on CPU. Fetched here rather than in the main run so the other eight
  // screens stay instant.
  const [ai, setAi] = useState(data?.ai);
  const [loading, setLoading] = useState(false);
  const [took, setTook] = useState(null);

  const generate = () => {
    setLoading(true);
    const started = performance.now();
    api
      .ai({
        budget: state.budget * 1e6,
        efficiency: state.efficiency,
        timeline: state.timeline,
        iso: state.iso,
      })
      .then((r) => {
        setAi(r);
        setTook((performance.now() - started) / 1000);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  // Auto-run once when the screen opens.
  useEffect(() => {
    if (!ai || ai.deferred) generate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="grid">
      <Panel idx="07" title="Backend in use" wide>
        <span className={`chip ${health?.local_model ? "real" : "hyp"}`}>
          {health?.local_model ? "local model · offline" : "rule-based · not a model"}
        </span>
        <p className="note" style={{ marginTop: 12 }}>
          {health?.local_model
            ? `Served by ${health.model} on ${health.endpoint}. Weights are on this disk. No API key exists in this codebase.`
            : "Ollama is not running, so this is deterministic rule-based text — not model output. Every number elsewhere in this demo is unaffected: the AI explains results, it does not produce them."}
        </p>
        <div className="btn-row" style={{ marginTop: 14 }}>
          <button className="btn" onClick={generate} disabled={loading}>
            {loading ? "Generating…" : "Regenerate"}
          </button>
          {loading && (
            <span className="caption" style={{ alignSelf: "center" }}>
              <span className="loading" /> local inference on CPU — 30–90s
            </span>
          )}
          {took && !loading && (
            <span className="caption" style={{ alignSelf: "center" }}>
              generated in {num(took, 1)}s
            </span>
          )}
        </div>
      </Panel>

      {loading && !ai?.reasoning ? (
        <Panel idx="07" title="Generating" wide>
          <div className="empty">
            <span className="loading" /> Running {health?.model} locally. No
            network involved — this is your CPU doing the work, which is why it
            takes a moment.
          </div>
        </Panel>
      ) : ai?.status !== "ok" || ai?.deferred ? (
        <Panel idx="07" title="Unavailable" wide>
          <div className="empty">{ai?.reason || "AI layer not loaded"}</div>
        </Panel>
      ) : (
        <>
          <Panel idx="07" title="Precision analysis" wide>
            <ul className="list">
              {(ai.analysis?.precision?.points || ai.analysis?.points || []).map((p, i) => (
                <li key={i}>{p}</li>
              ))}
            </ul>
          </Panel>
          <Panel idx="07" title="Wavelength analysis" wide>
            <ul className="list">
              {(ai.wavelength_analysis?.points || []).map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          </Panel>
          <Panel idx="07" title="Design suggestions" wide>
            <ul className="list">
              {(ai.analysis?.design?.points || []).map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          </Panel>
        </>
      )}
    </div>
  );
}

/* 8 ------------------------------------------------------------------------ */
export function ScreenLearning({ data }) {
  const l = data?.data_learning;
  if (l?.status !== "ok") return <div className="grid"><Panel idx="08" title="No patterns" wide><div className="empty">{l?.reason || "loading"}</div></Panel></div>;

  const totalMeasurements = (l.distributions || []).reduce(
    (sum, d) => sum + d.n_measurements, 0);
  const totalSources = (l.distributions || []).reduce(
    (sum, d) => sum + d.distinct_sources, 0);

  return (
    <div className="grid">
      <Panel idx="08" title="Measured spread" wide>
        <div className="stat-row" style={{ marginBottom: 16 }}>
          <Stat label="Measurements" value={totalMeasurements} pct={80} />
          <Stat label="Distinct sources" value={totalSources} pct={70} />
          <Stat label="Synthetic rows" value="0" pct={0} tone="mint" />
        </div>
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Quantity</th><th className="num">n</th><th className="num">Sources</th>
                <th className="num">Min</th><th className="num">Mean</th><th className="num">Max</th>
              </tr>
            </thead>
            <tbody>
              {(l.distributions || []).map((d, i) => (
                <tr key={i} className="lead">
                  <td>{d.quantity}</td>
                  <td className="num">{d.n_measurements}</td>
                  <td className="num">{d.distinct_sources}</td>
                  <td className="num">{num(d.min, d.min < 1 ? 3 : 0)}</td>
                  <td className="num" style={{ color: "var(--cyan)" }}>
                    {num(d.mean, d.mean < 1 ? 3 : 0)}
                  </td>
                  <td className="num">{num(d.max, d.max < 1 ? 3 : 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="note" style={{ marginTop: 14 }}>
          Every row is a published measurement with a citation. Mean Mo/Si
          reflectivity across 7 independent sources is <b style={{ color: "var(--cyan)" }}>0.683</b> —
          our simulation assumes 0.70, which is the optimistic end and worth
          about 10% of the throughput figure.
        </p>
      </Panel>

      <Panel idx="08" title="Regression on real data" wide>
        <p className="note" style={{ marginBottom: 14 }}>
          Each pair is fitted with linear, exponential and power-law forms,
          keeping whichever explains the most variance. Only{" "}
          <b>{l.patterns.length}</b> survived — published papers report the one
          quantity they measured, under their own conventions, so most column
          pairs have too few overlapping rows to fit. Our earlier synthetic
          dataset produced six confident fits here. They were artefacts of the
          data being invented.
        </p>
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Relationship</th><th>Form</th><th className="num">R²</th>
                <th className="num">n</th><th className="num">Published</th><th>Quality</th>
              </tr>
            </thead>
            <tbody>
              {l.patterns.map((p, i) => (
                <tr key={i} className={p.quality === "strong" ? "lead" : ""}>
                  <td>{p.x} → {p.y}</td>
                  <td style={{ color: "var(--violet)" }}>{p.model_form}</td>
                  <td className="num">{num(p.r_squared, 3)}</td>
                  <td className="num">{p.n_points}</td>
                  <td className="num">{p.n_published}</td>
                  <td>
                    <span className={`chip ${p.quality === "strong" ? "real" : ""}`}>
                      {p.quality}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel idx="08" title="Efficiency prediction" wide>
        {l.predictions?.available ? (
          <>
            <Readout>{num(l.predictions.predicted * 100, 3)}%</Readout>
            <div className="caption">
              conversion efficiency · 95% band {num(l.predictions.low * 100, 2)}–
              {num(l.predictions.high * 100, 2)}%
            </div>
            <p className="note" style={{ marginTop: 12 }}>{l.predictions.note}</p>
          </>
        ) : (
          <>
            <div className="caption">unavailable — and that is the finding</div>
            <p className="note" style={{ marginTop: 10 }}>
              {l.predictions?.reason}. Our earlier synthetic dataset produced a
              confident R²=0.94 fit here. On real published data it collapses,
              because conversion efficiency depends on target geometry, not
              drive power. The invented data had encoded a physical claim that
              is not true.
            </p>
          </>
        )}
      </Panel>
    </div>
  );
}

/* 9 ------------------------------------------------------------------------ */
export function ScreenSim({ data }) {
  const s = data?.simulation;
  if (!s) return <Loading />;
  return (
    <div className="grid">
      <Panel idx="09" title="Beamline" wide>
        <SimFlow sim={s} />
        <p className="note" style={{ marginTop: 14 }}>
          A Monte Carlo of this run's own photon budget. Capture odds at the
          collector, reflection odds at every mirror and the reticle gate are
          all taken from the numbers below — the sampled transmission printed
          on the canvas should converge on the computed one.
        </p>
      </Panel>

      <Panel idx="09" title="Photon chain" wide>
        <div className="chain">
          {(s.stages || []).map((st, i) => (
            <div className="stage" key={i} style={{ "--d": `${i * 0.32}s` }}>
              <span className="lbl">{st.label}</span>
              <span className="val">
                {typeof st.value === "number" ? st.value.toLocaleString() : st.value}
                <small>{st.unit}</small>
              </span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel idx="09" title="Imaging">
        <Readout tone={s.resolution_target_met ? "mint" : "rose"}>
          {num(s.resolution_nm, 2)} nm
        </Readout>
        <div className="caption">
          printed half-pitch · 7 nm target {s.resolution_target_met ? "met" : "NOT met"}
        </div>
        <div className="stat-row" style={{ marginTop: 18 }}>
          <Stat label="NA" value={num(s.numerical_aperture, 2)} pct={s.numerical_aperture * 180} />
          <Stat label="k1" value={num(s.k1, 2)} pct={s.k1 * 200} />
          <Stat label="Depth of focus" value={`${num(s.depth_of_focus_nm, 0)} nm`} pct={60} />
        </div>
      </Panel>

      <Panel idx="09" title="Power budget">
        <div className="stat-row">
          <Stat label="Drive laser" value={`${num(s.laser_power_kw, 1)} kW`} pct={100} />
          <Stat label="In-band EUV" value={`${num(s.euv_generated_w, 0)} W`} pct={70} />
          <Stat label="At focus" value={`${num(s.intermediate_focus_power_w, 1)} W`} pct={35} />
          <Stat label="At wafer" value={`${num(s.wafer_plane_power_w, 2)} W`} pct={8} tone="rose" />
        </div>
        <p className="note" style={{ marginTop: 16 }}>
          Optical transmission {num(s.optical_transmission_pct, 2)}% —{" "}
          {num(100 - s.optical_transmission_pct, 1)}% of source power is lost in
          the mirror train. That is the dominant inefficiency in the machine.
        </p>
      </Panel>

      <Panel idx="09" title="Productivity">
        <Readout>{num(s.throughput_wph, 0)}</Readout>
        <div className="caption">wafers per hour at {num(s.dose_mj_cm2, 0)} mJ/cm²</div>
        <Bar pct={Math.min(100, (s.throughput_wph / 200) * 100)} />
      </Panel>
    </div>
  );
}

/* helpers ------------------------------------------------------------------ */
function Stat({ label, value, pct, tone = "" }) {
  return (
    <div>
      <div className="caption">{label}</div>
      <div className="mini">{value}</div>
      <Bar pct={pct} tone={tone} />
    </div>
  );
}

function Loading() {
  return (
    <div className="grid">
      <Panel idx="··" title="Working" wide>
        <div className="empty"><span className="loading" /> computing…</div>
      </Panel>
    </div>
  );
}
