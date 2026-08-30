# EUV Components Optimizer

Exhaustive search over EUV lithography component configurations, under real
engineering constraints.

An EUV scanner is assembled from thousands of parts, and the conventional path
to a new machine is design → build → test → fail → redesign. Each loop is
expensive. This tool moves the search earlier: it enumerates **every one of
19,440 possible component configurations**, scores each against cost,
efficiency, build timeline and cleanroom class, and returns the ones that
actually satisfy the constraints — before anything is built.

Not a sample. Not a heuristic. Every configuration is evaluated.

**Live demo:** http://ec2-15-252-182-253.ap-south-1.compute.amazonaws.com/

---

## What it does

Set four constraints — capital budget, minimum efficiency, build timeline,
cleanroom ISO class — and the engine re-ranks the full configuration space
against them. A representative run at the default settings evaluates 19,440
configurations and finds **2,532 feasible**.

Results are presented across nine screens:

| # | Screen | What it shows |
|---|--------|---------------|
| 1 | User Input | The four constraints, with the physical limit beside each |
| 2 | Display Results | Top 5 configurations, cost, savings, parts mapping |
| 3 | Visualization | Cost vs baseline, subsystem split, trade-off frontier |
| 4 | Interactivity | Inverse solve — pin what you know, solve for the rest |
| 5 | Particle Management | Contamination risk and its effect on die yield |
| 6 | Cleanliness | ISO class trade-off: cleanroom cost against yield loss |
| 7 | AI Precision & Design | Reasoning layer explaining the selected configuration |
| 8 | External Data Learning | Published measurements underpinning the model |
| 9 | EUV Simulation | Physics chain, drive laser through to wafer |

## Honesty about the numbers

This project's central claim is that the search is exhaustive and the inputs
are disclosed — so the numbers carry their own caveats rather than hiding them:

- Every value either **carries a citation or is labelled as an estimate**. The
  UI reports the sourced percentage on the home screen.
- Configurations containing parts that do not exist as commercial products are
  flagged **"not real"** in the results table rather than quietly included.
- Cost and timeline figures are **model outputs**, not experimentally validated
  results. They are presented as projections.
- The AI layer is labelled `local model` or `rule-based` depending on whether
  Ollama is actually running. It never claims to be a model when it is not.

`SECURITY.md` documents the network behaviour and the AI architecture in
detail, including where the project's own slide deck overstated things.

## Architecture

```
constraints ─→ optimizer ─→ constraint filter ─→ ranked configurations
                                                        │
                                    AI layer explains ──┘
```

**Backend** — Python, **standard library only**. No pip install, no framework,
no third-party runtime dependency. `serve.py` runs a threaded HTTP server on
port 8000 and serves both the API and the built frontend.

**Frontend** — React 18 + Vite. Two runtime dependencies (`react`,
`react-dom`).

**AI layer** — optional. Probes Ollama on `127.0.0.1:11434`. If no model is
present the system falls back to deterministic rule-based output and says so;
the demo never dies mid-pitch.

## Running it

Requires Python 3.10+ and Node 18+.

Build the frontend once:

```bash
cd web && npm install && npm run build
```

Then start the server from the repository root:

```bash
python serve.py
```

Open http://localhost:8000. The server binds loopback by default; set `PORT`
to change the port.

## API

Ten JSON routes, all served from the same process:

| Route | Purpose |
|-------|---------|
| `/api/run` | Full optimisation run — the main endpoint |
| `/api/health` | Backend and local-model status |
| `/api/solve` | Inverse solve for an unknown parameter |
| `/api/frontier` | Cost/efficiency trade-off frontier |
| `/api/design` | Design optimisation toward a named goal |
| `/api/alternatives` | Alternative parts for a category |
| `/api/cost-reduction` | Routes to a target cost |
| `/api/compare-goals` | Compare optimisation objectives |
| `/api/goals` | Available goals |
| `/api/ai` | Reasoning and precision analysis |

`BACKEND_CONTRACT.md` documents the response schema (currently `1.0.0`).

Malformed input is handled rather than crashing: bad values are coerced or
rejected with `400`, and a sweep across the full input range plus hostile
inputs returns no `500`s.

## Deployment

`DEPLOY.md` covers deployment to AWS EC2 behind nginx, including the systemd
unit and the update procedure. `deploy/` holds the supporting files, and a
`Dockerfile` is included.

## Repository map

| Path | Contents |
|------|----------|
| `serve.py`, `backend.py` | HTTP server and orchestration |
| `optimizer.py`, `solver.py` | Search and constraint satisfaction |
| `cost_optimizer.py`, `cost_advisor.py` | Cost models |
| `particle_manager.py`, `euv_simulation.py` | Contamination and physics |
| `disclosure.py`, `reconcile.py` | Sourcing disclosure and validation |
| `ai/` | Local model client and the knowledge pipeline |
| `data/` | Component data, sourcing appendix, validation report |
| `web/` | React frontend |

## Documentation

| Document | Covers |
|----------|--------|
| `SECURITY.md` | Network behaviour, AI architecture, honest corrections |
| `BACKEND_CONTRACT.md` | API response schema |
| `DEPLOY.md` | AWS EC2 deployment |
| `REHEARSAL.md` | Demo runbook |
| `data/VALIDATION_REPORT.md` | Validation of the component data |
| `data/SOURCING_APPENDIX.md` | Where each figure comes from |

---


