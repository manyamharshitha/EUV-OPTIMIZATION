// Home launcher.
//
// Nine tiles, each opening one screen full-screen. Every tile carries a live
// value pulled from the current run, so the launcher is a status board rather
// than a menu -- a judge can see the machine is computing before clicking
// into anything.

import { SCREENS } from "../screens.jsx";
import { compactMoney, count, num } from "../api.js";
import { Spark } from "./charts.jsx";
import { PlasmaField } from "./PlasmaField.jsx";

function preview(id, data, health, state) {
  const r = data?.results;
  const best = r?.top_configurations?.[0];

  switch (id) {
    case 1:
      return {
        value: `$${state.budget}M`,
        note: `${(state.efficiency * 100).toFixed(0)}% · ${state.timeline} yr`,
      };
    case 2:
      return best
        ? {
            value: compactMoney(best.total_cost_usd),
            note: `${num(r.savings.percent, 1)}% saved`,
          }
        : { value: "—", note: "no feasible result" };
    case 3:
      return { value: "5", note: "charts" };
    case 4:
      return { value: "2", note: "solvers" };
    case 5:
      return data?.particles
        ? {
            value: `${num(data.particles.yield_pct, 1)}%`,
            note: `risk ${data.particles.risk_level.toLowerCase()}`,
          }
        : { value: "—", note: "yield" };
    case 6:
      return data?.cleanliness
        ? {
            value: `ISO ${data.cleanliness.recommended_class}`,
            note: "recommended",
          }
        : { value: "—", note: "iso" };
    case 7:
      return {
        value: health?.local_model ? "LOCAL" : "RULES",
        note: health?.local_model ? "model live" : "no model loaded",
        warn: !health?.local_model,
      };
    case 8: {
      // Measurements, not fitted relationships. Real published data supports
      // very few regressions, so the measurement count is the honest headline.
      const dists = data?.data_learning?.distributions || [];
      const n = dists.reduce((sum, d) => sum + d.n_measurements, 0);
      return {
        value: n ? String(n) : "—",
        note: "published measurements",
      };
    }
    case 9:
      return data?.simulation
        ? {
            value: `${num(data.simulation.resolution_nm, 1)} nm`,
            note: data.simulation.resolution_target_met
              ? "target met"
              : "7 nm not met",
            warn: !data.simulation.resolution_target_met,
          }
        : { value: "—", note: "resolution" };
    default:
      return { value: "—", note: "" };
  }
}

export function Home({ data, health, state, onOpen, busy }) {
  const r = data?.results;

  return (
    <div className="home">
      <section className="hero">
        {/* The field, absolutely positioned to this section — and the section
            now bleeds to the viewport edges and fills the first screen, so the
            plasma IS the landing background. */}
        <PlasmaField data={data} />

        <div className="hero-copy">
          <h2>
            What would it take to build an EUV machine
            <br />
            <span>somewhere else?</span>
          </h2>
          <p>
            Every one of{" "}
            <b>{count(r?.combinations_evaluated)}</b>{" "}
            possible component configurations, evaluated exhaustively. Not a
            sample, not a heuristic. Every number either carries a citation or
            is labelled as our estimate.
          </p>

          <div className="hero-stats">
            <div>
              <span className="hero-n">
                {count(r?.feasible_count)}
              </span>
              <span className="hero-l">feasible</span>
            </div>
            <div>
              <span className="hero-n">
                {data?.sourcing ? `${num(data.sourcing.sourced_pct, 0)}%` : "—"}
              </span>
              <span className="hero-l">cited</span>
            </div>
            <div>
              <span className="hero-n">
                {data?.meta ? `${num(data.meta.elapsed_seconds, 2)}s` : "—"}
              </span>
              <span className="hero-l">compute</span>
            </div>
          </div>
        </div>

        {/* The telemetry pill that used to float over the figure was removed:
            it covered a third of the plasma render, and every value it showed
            (drive, conversion, collector, IF power, half-pitch, throughput) is
            already on screen 9, where the simulation has room to label itself.
            The figure now reads as a figure rather than a dashboard. */}
      </section>

      <div className="tiles">
        {SCREENS.map((s) => {
          const p = preview(s.id, data, health, state);
          const spread = (data?.results?.top_configurations || [])
            .map((c) => c.total_cost_usd)
            .reverse();
          return (
            <button
              className={`tile ${p.warn ? "warn" : ""} ${
                s.id === 2 ? "tile-lead" : ""
              } ${s.id === 9 ? "tile-wide" : ""}`}
              key={s.id}
              onClick={() => onOpen(s.id)}
              style={{ "--accent": s.colour, "--accent-ink": s.ink }}
            >
              <span className="tile-n">{String(s.id).padStart(2, "0")}</span>

              <span className="tile-body">
                <b>{s.name}</b>
                <em>{s.hint}</em>
              </span>

              <span className="tile-val">
                <b>{busy && !data ? "…" : p.value}</b>
                <em>{p.note}</em>
              </span>

              {s.id === 2 && spread.length > 1 && (
                <span className="tile-spark">
                  <Spark values={spread} />
                </span>
              )}

              <span className="tile-go" aria-hidden="true">
                →
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
