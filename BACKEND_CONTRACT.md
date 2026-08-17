# backend.py contract — B → D

Agree this **Day 1 morning, before anyone writes code.** If B and D disagree
about the shape of this dictionary, Day 2 is lost to integration hell.

Schema version: **1.0.0** (`result["meta"]["schema_version"]`)

## The only call D makes

```python
from backend import run

result = run(
    budget_usd=180_000_000,
    min_efficiency=0.50,
    max_timeline_years=8.0,
    iso_class=3,
    dose_mj_cm2=30.0,
    target_resolution_nm=7.0,
)
```

D does **not** import `optimizer`, `euv_simulation` or `particle_manager`.
One call, one dictionary.

## Guarantees B makes

1. `run()` never raises. Failures land in `result["errors"]` as strings.
2. `result["ok"]` is `True` whenever the run completed, even if constraints
   were too tight to yield an answer. Check `results.top_configurations` for
   emptiness, not `ok`.
3. Every key below always exists. Values may be `None`; keys never vanish.
4. No network access, ever. Verified by `demo_proof.py` claim 9.
5. Typical response is **under 100 ms**. Worst measured slider position: 60 ms.

## Top-level keys → screens

| Key | Screen | Notes |
|---|---|---|
| `meta` | — | schema version, elapsed time |
| `user_input` | 1. User Input | echo of what was asked |
| `results` | 2. Display Results | top 5 + baseline + savings |
| `visualization` | 3. Visualization | chart-ready series |
| `interactivity` | 4. Interactivity | slider bounds |
| `particles` | 5. Particle Management | contamination report |
| `cleanliness` | 6. Cleanliness | all 9 ISO classes compared |
| `ai` | 7. AI Precision & Design | C's modules, optional |
| `data_learning` | 8. External Data Learning | C's modules, optional |
| `simulation` | 9. EUV Simulation | full physics chain |
| `sourcing` | honesty slide | cited vs MODELED counts |
| `disclosure` | **every screen** | **see below — this one is mandatory** |
| `errors` | — | list of strings, empty on success |
| `ok` | — | bool |

## `disclosure` — read this before building anything

Added after the first version of this contract. If D built to the old
version, this key is being ignored, and that is the single most damaging
thing that can happen to this submission.

It carries the sentences the project has to say about itself **before a judge
works them out independently**. Each is computed live from the run that
produced it, so it can never drift from the number it qualifies.

```python
result["disclosure"] = {
    "count": 4,
    "must_state_count": 2,
    "must_state": [
        {"id": "ai_backend", "severity": "critical", "say": "..."},
        {"id": "cost_basis",  "severity": "high",     "say": "..."},
    ],
    "entries": [
        {
            "id": "hypothetical_components",
            "severity": "critical" | "high" | "medium" | "low",
            "headline": "7 of 8 parts in this configuration (88%) DO NOT EXIST...",
            "detail": "longer explanation",
            "say_this": "the sentence to speak out loud",
            "chosen_hypothetical": 7,
            "chosen_total": 8,
            "parts": [{"category": ..., "name": ..., "country": ...}],
        },
        # cost_basis, ai_backend, resolution_target
    ],
    "frontend_contract": "...",
}
```

**What D must build:**

| Requirement | Why |
|---|---|
| Render `headline` for every `critical` and `high` entry **beside the number it qualifies** — not in a footer, tooltip, or About page | A disclosure a judge has to go looking for does not count as having disclosed it |
| Style `critical` so it is impossible to miss (red band, not grey italics) | The critical ones are the ones that end the pitch if discovered first |
| Re-read on **every** run — never cache | Severity changes with the configuration. The default config is all-real parts; a cost-focused one is 88% vaporware. A cached "low" over an 88% result is worse than showing nothing |
| Show `ai_backend` state as a persistent badge on screens 7 and 8 | `rule_based` and `local_model` are different claims and must never look alike |

**Concrete case D must handle.** Move the weights to cost-focused and the
optimizer selects 7 of 8 components that do not exist. `severity` flips to
`critical` and `chosen_hypothetical` becomes 7. If the UI shows the 27%
saving without that band, the demo is claiming a cost reduction from parts
nobody can buy — and it is the biggest saving on screen, so it is the one a
judge will ask about.

`demo_proof.py` claim 11 verifies the payload carries these and that the
counts match the actual configuration. It does not and cannot verify that D
renders them.

## Shapes D will actually index

```python
result["results"]["top_configurations"]          # list, length 5 (or 0)
result["results"]["top_configurations"][0]["rank"]              # 1
result["results"]["top_configurations"][0]["total_cost_usd"]    # float
result["results"]["top_configurations"][0]["efficiency_pct"]    # float
result["results"]["top_configurations"][0]["timeline_years"]    # float
result["results"]["top_configurations"][0]["components"]        # list of dicts
result["results"]["baseline"]                    # same shape, or None
result["results"]["savings"]["absolute_usd"]     # float
result["results"]["savings"]["percent"]          # float
result["results"]["combinations_evaluated"]      # int — say this out loud

result["visualization"]["cost_bar"]              # [{label, value, is_baseline}]
result["visualization"]["cost_pie"]              # [{label, value, name}]
result["visualization"]["timeline"]              # [{label, years}]
result["visualization"]["efficiency"]            # [{label, value}]
result["visualization"]["simulation_stages"]     # [{label, value, unit}]
result["visualization"]["parts_mapping"]         # [{original_*, replacement_*, saving_usd}]

result["simulation"]["resolution_nm"]            # float
result["simulation"]["resolution_target_met"]    # bool  <- the 7 nm proof
result["simulation"]["throughput_wph"]           # float
result["simulation"]["stages"]                   # ordered pipeline

result["particles"]["risk_level"]                # MINIMAL|LOW|MODERATE|HIGH|CRITICAL
result["particles"]["yield_pct"]                 # float
result["particles"]["recommendation"]            # sentence, display verbatim

result["cleanliness"]["comparison"]              # 9 rows, cheapest first

result["ai"]["status"]                           # ok|unavailable|error
result["ai"]["reasoning"]                        # str or None — GUARD THIS
```

**D: always guard the AI fields.** `result["ai"]["status"]` is `unavailable`
until C's files exist, and `reasoning` is `None` in that case. Render a
placeholder, not a crash. Same for `data_learning`.

## Interface B needs from C

B calls these lazily and tolerates their absence. C should provide:

```python
# ai_local_claude.py
explain_choice(config: dict) -> str
analyse_configuration(config: dict, simulation: dict) -> str
analyse_wavelength(simulation: dict) -> str

# data_learner.py
extract_patterns() -> list
predict_efficiency() -> list
```

## Interface B needs from A

`components.csv` with these columns:

```
component_id, category, name, supplier, country, cost_usd, efficiency,
lead_time_years, is_baseline, specs_json, source, confidence
```

- `efficiency` — 0..1. Multiplied across categories, not averaged.
- `is_baseline` — `1` on exactly one row per category (the ASML reference).
  Without these, cost comparison and parts mapping return `None`.
- `specs_json` — JSON object. Physics keys the simulation reads:
  `laser_power_kw`, `conversion_efficiency`, `collector_reflectivity`,
  `collection_solid_angle_sr`, `mirror_count`, `mirror_reflectivity`,
  `numerical_aperture`, `k1`. Missing keys fall back to defaults.
- `source` — citation, or the literal string `MODELED`.
- `confidence` — `HIGH` | `MEDIUM` | `LOW`.

`sample_data/components.csv` is a **placeholder** so B could build and test
before the Day 1 handoff. Every row is `MODELED`. Point `run()` at A's real
file via `components_csv=`, or replace the file.

## Known limitations B must be able to defend

1. **ISO particle sizes clamp at 0.1 µm.** The ISO 14644-1 formula is only
   defined down to 0.1 µm. Killer particles at 7 nm are ~3.5 nm, far below
   that, so the concentration lookup clamps. Consequence: below ~100 nm
   resolution, changing the resolution does not change the modelled particle
   concentration. If a judge probes contamination scaling, say this plainly —
   do not pretend the model resolves it.

2. **Efficiency is a unitless 0..1 proxy**, not a measured physical
   efficiency. It is multiplicative because the machine is an optical chain.
   That is a modelling choice, defensible but not sourced.

3. **`SCAN_DUTY_FACTOR = 0.30` is calibrated, not derived.** It was fitted so
   a 250 W source lands at ~150 wph, matching published NXE:3400B figures.
   Marked CALIBRATED in the source.

4. **Cleanroom costs are modelled**, not quoted. Person A must source these
   or the honesty slide must flag them.

## Cut order impact on B

Per the workplan, if the team falls behind, `particle_manager.py` is the only
B-owned module on the drop list. Removing it costs `result["particles"]` and
`result["cleanliness"]` — screens 5 and 6 — and nothing else breaks.
`optimizer.py`, `euv_simulation.py` and `demo_proof.py` are marked never-cut.

## Verify before the demo

```bash
python demo_proof.py
```

38 claims, exit code 0. Run it on the second laptop from a clean clone.
