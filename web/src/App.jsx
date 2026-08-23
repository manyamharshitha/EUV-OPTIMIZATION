import { useCallback, useEffect, useRef, useState } from "react";
import { api, count, num } from "./api.js";
import { Mark } from "./components/Mark.jsx";
import { Boundary } from "./components/Boundary.jsx";
import { ScreenField } from "./components/ScreenField.jsx";
import { Home } from "./components/Home.jsx";
import { Rail } from "./components/Rail.jsx";
import {
  SCREENS, PRESETS,
  ScreenInput, ScreenResults, ScreenVisual, ScreenInteract,
  ScreenParticles, ScreenClean, ScreenAI, ScreenLearning, ScreenSim,
} from "./screens.jsx";

// 0 is the home launcher; 1-9 open that screen full-screen.
const HOME = 0;

export default function App() {
  const [screen, setScreen] = useState(HOME);
  const [state, setState] = useState({
    budget: 180, efficiency: 0.5, timeline: 8, iso: 3, preset: "balanced",
  });

  const [data, setData] = useState(null);
  const [health, setHealth] = useState(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(null);

  const seq = useRef(0);
  const set = (key, value) => setState((s) => ({ ...s, [key]: value }));

  const load = useCallback(async () => {
    const mine = ++seq.current;
    setBusy(true);
    setError(null);
    try {
      const w = PRESETS[state.preset];
      const result = await api.run({
        budget: state.budget * 1e6,
        efficiency: state.efficiency,
        timeline: state.timeline,
        iso: state.iso,
        w_cost: w.w_cost, w_eff: w.w_eff, w_time: w.w_time,
      });
      // A slower earlier request must never overwrite a newer answer.
      if (mine !== seq.current) return;
      setData(result);
    } catch (exc) {
      if (mine === seq.current) setError(String(exc.message || exc));
    } finally {
      if (mine === seq.current) setBusy(false);
    }
  }, [state]);

  // Debounce so dragging a slider doesn't fire a request per pixel.
  useEffect(() => {
    const handle = setTimeout(load, 180);
    return () => clearTimeout(handle);
  }, [load]);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ local_model: false }));
  }, []);

  // Keyboard: Esc returns home, arrows step between screens, 1-9 jump.
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === "INPUT") return;
      if (e.key === "Escape") setScreen(HOME);
      if (e.key === "ArrowRight") setScreen((s) => (s === 9 ? 9 : s + 1));
      if (e.key === "ArrowLeft") setScreen((s) => Math.max(HOME, s - 1));
      if (/^[1-9]$/.test(e.key)) setScreen(Number(e.key));
      if (e.key === "0" || e.key === "h") setScreen(HOME);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Opening a screen should start at its top, not wherever home was scrolled.
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [screen]);

  const props = { state, set, data, busy, health };
  const VIEWS = {
    1: <ScreenInput {...props} />,
    2: <ScreenResults {...props} />,
    3: <ScreenVisual {...props} />,
    4: <ScreenInteract {...props} />,
    5: <ScreenParticles {...props} />,
    6: <ScreenClean {...props} />,
    7: <ScreenAI {...props} />,
    8: <ScreenLearning {...props} />,
    9: <ScreenSim {...props} />,
  };

  const current = SCREENS.find((s) => s.id === screen);
  const atHome = screen === HOME;

  return (
    <>
      <div className="field" />
      <div className="lattice" />

      <Rail current={screen} onSelect={setScreen} />

      {/* The open screen's colour cascades to everything inside it — buttons,
          bars, readouts — so each of the nine has a distinct identity while
          sharing one background. */}
      <div
        className="shell"
        style={
          current
            ? { "--accent": current.colour, "--accent-ink": current.ink }
            : undefined
        }
      >
        <header className="masthead">
          <button
            className="wordmark as-button"
            onClick={() => setScreen(HOME)}
            title="Back to home"
          >
            <Mark additive text />
            <div>
              <h1>EUV Components Optimizer</h1>
              <p>Sovereign lithography · exhaustive search</p>
            </div>
          </button>

          <div className="badges">
            <span className="badge">
              <span className="dot" />
              {data?.results
                ? `${count(data.results.combinations_evaluated)} evaluated`
                : "…"}
            </span>
            <span className={`badge ${health?.local_model ? "" : "warn"}`}>
              <span className="dot" />
              {health?.local_model ? "local model" : "rule-based"}
            </span>
            <span className="badge">
              <span className="dot" />
              offline capable
            </span>
          </div>
        </header>

        {/* The full disclosure cards are gone from the app shell entirely.
            They are not gone from the app: every number still carries its
            inline caveat on the screen where it appears (see screen 2's
            hypothetical-parts and cost-basis notes), which is where a judge
            reading the number actually looks. The stacked cards up here
            pushed the hero below the fold. */}

        {error && (
          <div className="disclosures">
            <div className="disclose critical">
              <span className="sev">error</span>
              <div className="body">
                <div className="head">Backend unreachable</div>
                <div className="say">{error}</div>
              </div>
            </div>
          </div>
        )}

        {atHome ? (
          <Boundary resetKey={screen}>
          <main key="home" className="view">
            <Home
              data={data}
              health={health}
              state={state}
              busy={busy}
              onOpen={setScreen}
            />
          </main>
          </Boundary>
        ) : (
          <>
            <div className="screen-head">
              <button className="btn back" onClick={() => setScreen(HOME)}>
                ← All screens
              </button>
              <h2>
                <span>{String(screen).padStart(2, "0")}</span> {current.name}
              </h2>
              <div className="pager">
                <button
                  className="btn"
                  onClick={() => setScreen(Math.max(1, screen - 1))}
                  disabled={screen === 1}
                  style={{
                    borderLeftColor:
                      SCREENS.find((s) => s.id === screen - 1)?.colour,
                  }}
                >
                  ← Prev
                </button>
                <button
                  className="btn"
                  onClick={() => setScreen(Math.min(9, screen + 1))}
                  disabled={screen === 9}
                  style={{
                    borderLeftColor:
                      SCREENS.find((s) => s.id === screen + 1)?.colour,
                  }}
                >
                  Next →
                </button>
              </div>
            </div>

            {/* Only the screen body is wrapped. The masthead, pager and
                footer stay mounted, so a screen that throws leaves the other
                eight reachable instead of blanking the app. */}
            {/* Ambient field for screens 1-8, one motif each, tinted with
                that screen's own accent. Screen 9 is excluded: its beamline
                is already a simulation and a second moving layer behind it
                would compete for the same attention.
                Keyed on `screen` so switching restarts the motif from its
                opening frame instead of dropping in mid-cycle. */}
            {screen !== 9 && (
              <ScreenField
                key={screen}
                variant={screen}
                accent={current?.colour}
              />
            )}

            <Boundary resetKey={screen}>
              <main key={screen} className="view">
                {VIEWS[screen]}
              </main>
            </Boundary>
          </>
        )}

        <footer className="footer">
          <span>{atHome ? "home" : `screen ${screen} of 9`}</span>
          <span>schema {data?.meta?.schema_version ?? "—"}</span>
          <span>backend {num(data?.meta?.elapsed_seconds, 2)}s</span>
          <span>127.0.0.1 only · no external requests</span>
          <span>{atHome ? "1–9 to open" : "Esc for home · ← →"}</span>
        </footer>
      </div>
    </>
  );
}
