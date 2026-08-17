"""
backend.py  --  Person B (Algorithm Engineer)

THE single entry point.  Person D calls exactly one function:

    from backend import run
    result = run(budget_usd=180e6, min_efficiency=0.55, max_timeline_years=6.0)

and gets back one dictionary containing everything needed to paint all nine
screens.  D never imports optimizer, euv_simulation or particle_manager
directly.  If the shape of this dictionary changes, B tells D first.

Design rules for this file:

  1. run() does not raise during a live demo.  Any failure is caught and
     reported inside result["errors"], with every other screen still
     populated where possible.  A judge must never see a traceback.
  2. Person C's AI modules are optional.  They are imported lazily inside a
     try/except.  If Ollama is not running, or C's files do not exist yet,
     the AI screens report status "unavailable" and the rest of the demo is
     unaffected.  This is also the cut-order safety net.
  3. No network calls, ever.  Everything here is local computation.
"""

from __future__ import annotations

import os
import sys
import time
import traceback

import optimizer
import euv_simulation
import particle_manager

# Resolve data files relative to this file, so the demo works no matter which
# directory the judge launches it from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Person C's AI modules live in ai/. Put it on the path so the optional
# imports below can find them without C having to restructure their folder.
_AI_DIR = os.path.join(BASE_DIR, "ai")
if os.path.isdir(_AI_DIR) and _AI_DIR not in sys.path:
    sys.path.insert(0, _AI_DIR)

# Person A's sourced database (handoff A -> B, end of Day 1). Falls back to
# the placeholder fixtures if A's files are not in place yet.
_A_DATA = os.path.join(BASE_DIR, "data", "components.csv")
_FIXTURE = os.path.join(BASE_DIR, "sample_data", "components.csv")

DEFAULT_COMPONENTS_CSV = _A_DATA if os.path.exists(_A_DATA) else _FIXTURE
DEFAULT_PARTICLE_LIMITS = os.path.join(
    BASE_DIR, "data" if os.path.exists(_A_DATA) else "sample_data",
    "particle_limits.json")

RESULT_SCHEMA_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Optional AI layer (Person C)
# ---------------------------------------------------------------------------

def _ai_status_only() -> dict:
    """
    Which AI backend WOULD serve this run, without generating anything.

    The health probe is a cached sub-second call to loopback, so every run can
    afford it. That keeps `disclosure.py` honest about whether the panels are
    a real model or rule-based text, even when no analysis was generated.
    """
    try:
        import ai_local_claude
    except ImportError:
        return {"status": "unavailable", "reason": "ai_local_claude.py not present",
                "deferred": True, "reasoning": None, "analysis": None,
                "wavelength_analysis": None}

    health = ai_local_claude.model_available()
    live = health["available"] and health["target_model_present"]
    backend_name = "local_model" if live else "rule_based"

    return {
        "status": "ok",
        "deferred": True,
        "reason": "analysis not generated on this run -- call /api/ai",
        "reasoning": None,
        "analysis": {"backend": backend_name, "points": []},
        "wavelength_analysis": None,
    }


def _try_ai_analysis(config: dict, simulation: dict) -> dict:
    """
    Call Person C's local-Claude module if it exists.  Never let its absence
    or failure break the run.
    """
    try:
        import ai_local_claude  # Person C's file
    except ImportError:
        return {
            "status": "unavailable",
            "reason": "ai_local_claude.py not present",
            "reasoning": None,
            "analysis": None,
            "wavelength_analysis": None,
        }

    try:
        return {
            "status": "ok",
            # explain_choice() is deliberately not called. Screen 7 renders
            # precision, wavelength and design only, and on CPU every extra
            # model call is ~90 seconds of a judge waiting.
            "reasoning": None,
            "analysis": ai_local_claude.analyse_configuration(config, simulation),
            "wavelength_analysis": ai_local_claude.analyse_wavelength(simulation),
        }
    except Exception as exc:
        return {
            "status": "error",
            "reason": f"{type(exc).__name__}: {exc}",
            "reasoning": None,
            "analysis": None,
            "wavelength_analysis": None,
        }


def _try_data_learning() -> dict:
    """Call Person C's external-data pattern extraction if present."""
    try:
        import data_learner  # Person C's file
    except ImportError:
        return {
            "status": "unavailable",
            "reason": "data_learner.py not present",
            "patterns": [],
            "predictions": [],
        }

    try:
        return {
            "status": "ok",
            "patterns": data_learner.extract_patterns(),
            "predictions": data_learner.predict_efficiency(),
            # Published experimental data is sparse -- papers report the one
            # quantity they measured and leave the rest of the row empty. That
            # defeats pairwise regression on most column pairs, but the spread
            # of the measurements is itself a real result, so surface it
            # rather than showing an empty panel.
            "distributions": data_learner.distributions(),
        }
    except Exception as exc:
        return {
            "status": "error",
            "reason": f"{type(exc).__name__}: {exc}",
            "patterns": [],
            "predictions": [],
        }


# ---------------------------------------------------------------------------
# Honesty accounting
# ---------------------------------------------------------------------------

def _sourcing_summary(components: list) -> dict:
    """
    How many numbers in this run carry a real citation versus [MODELED].
    This is Person A's success measure, computed here so the frontend can
    display it on the honesty slide without recomputing.
    """
    total = len(components)
    sourced = sum(1 for component in components if component.is_sourced)

    by_confidence = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for component in components:
        by_confidence[component.confidence] = by_confidence.get(component.confidence, 0) + 1

    return {
        "total_components": total,
        "sourced": sourced,
        "modeled": total - sourced,
        "sourced_pct": round(sourced / total * 100.0, 1) if total else 0.0,
        "by_confidence": by_confidence,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(include_ai: bool = False,
        budget_usd: float = 180_000_000.0,
        min_efficiency: float = 0.50,
        max_timeline_years: float = 8.0,
        weight_cost: float = 0.45,
        weight_efficiency: float = 0.40,
        weight_time: float = 0.15,
        iso_class: int = 3,
        dose_mj_cm2: float = 20.0,
        target_resolution_nm: float = 7.0,
        required_countries: tuple = (),
        excluded_suppliers: tuple = (),
        top_n: int = 5,
        components_csv: str = None,
        particle_limits_json: str = None) -> dict:
    """
    Run the complete pipeline.

    Returns a dictionary with these top-level keys, one group per screen:

        meta                run metadata, timing, schema version
        user_input          echo of what was asked for (screen 1)
        results             top N configurations + baseline + savings (screen 2)
        visualization       chart-ready series (screen 3)
        interactivity       slider bounds and current values (screen 4)
        particles           contamination report (screen 5)
        cleanliness         ISO class comparison (screen 6)
        ai                  reasoning / analysis / wavelength (screens 7, 9-AI)
        data_learning       external data patterns (screen 8)
        simulation          full physics chain (screen 9)
        sourcing            citation accounting for the honesty slide
        errors              list of non-fatal failures
    """
    started = time.perf_counter()
    errors = []

    components_csv = components_csv or DEFAULT_COMPONENTS_CSV
    particle_limits_json = particle_limits_json or DEFAULT_PARTICLE_LIMITS

    result = {
        "meta": {
            "schema_version": RESULT_SCHEMA_VERSION,
            "components_csv": components_csv,
            "offline": True,
            "elapsed_seconds": None,
        },
        "user_input": {
            "budget_usd": budget_usd,
            "min_efficiency": min_efficiency,
            "max_timeline_years": max_timeline_years,
            "weights": {
                "cost": weight_cost,
                "efficiency": weight_efficiency,
                "time": weight_time,
            },
            "iso_class": iso_class,
            "dose_mj_cm2": dose_mj_cm2,
            "target_resolution_nm": target_resolution_nm,
            "required_countries": list(required_countries),
            "excluded_suppliers": list(excluded_suppliers),
        },
        "results": None,
        "visualization": None,
        "interactivity": None,
        "particles": None,
        "cleanliness": None,
        "ai": None,
        "data_learning": None,
        "simulation": None,
        "sourcing": None,
        "errors": errors,
        "ok": False,
    }

    # --- Load ---------------------------------------------------------------
    try:
        components = optimizer.load_components(components_csv)
    except Exception as exc:
        errors.append(f"Could not load components: {exc}")
        result["meta"]["elapsed_seconds"] = round(time.perf_counter() - started, 4)
        return result

    result["sourcing"] = _sourcing_summary(components)

    # --- Optimise -----------------------------------------------------------
    try:
        weight_total = weight_cost + weight_efficiency + weight_time
        if weight_total <= 0:
            weight_cost, weight_efficiency, weight_time = 0.45, 0.40, 0.15
            weight_total = 1.0

        weights = {
            "cost": weight_cost / weight_total,
            "efficiency": weight_efficiency / weight_total,
            "time": weight_time / weight_total,
        }

        constraints = optimizer.Constraints(
            max_budget_usd=budget_usd,
            min_efficiency=min_efficiency,
            max_timeline_years=max_timeline_years,
            required_countries=tuple(required_countries),
            excluded_suppliers=tuple(excluded_suppliers),
        )

        optimisation = optimizer.optimize(components, constraints, weights, top_n)
        result["results"] = optimisation
    except Exception as exc:
        errors.append(f"Optimisation failed: {exc}")
        traceback.print_exc()
        result["meta"]["elapsed_seconds"] = round(time.perf_counter() - started, 4)
        return result

    if not optimisation["top_configurations"]:
        # Not an error -- constraints were simply too tight.  Still give D the
        # interactivity bounds so the judge can loosen a slider and retry.
        result["interactivity"] = _interactivity_bounds(components, result["user_input"])
        result["meta"]["elapsed_seconds"] = round(time.perf_counter() - started, 4)
        result["ok"] = True
        return result

    best = optimisation["top_configurations"][0]

    # --- Physics ------------------------------------------------------------
    try:
        simulation = euv_simulation.simulate_from_config(
            best, dose_mj_cm2=dose_mj_cm2, target_resolution_nm=target_resolution_nm
        ).to_dict()
        result["simulation"] = simulation
    except Exception as exc:
        errors.append(f"Simulation failed: {exc}")
        simulation = {}

    resolution_nm = simulation.get("resolution_nm", target_resolution_nm)

    # --- Contamination ------------------------------------------------------
    try:
        report = particle_manager.assess(
            iso_class=iso_class,
            resolution_nm=resolution_nm,
            limits_path=particle_limits_json,
        )
        result["particles"] = report.to_dict()
        result["cleanliness"] = {
            "comparison": particle_manager.compare_all_classes(resolution_nm),
            "current_class": iso_class,
            "recommended_class": report.recommended_iso_class,
        }
    except Exception as exc:
        errors.append(f"Particle assessment failed: {exc}")

    # --- AI layer (Person C, optional) --------------------------------------
    # AI analysis is OPT-IN, and must stay that way.
    #
    # With a local model loaded, the three analyses cost five model calls at
    # 7-36 seconds each on CPU -- so folding them into every run turned a
    # 1.7 second pipeline into a two-minute one, and made dragging a slider
    # unusable. Only screen 7 needs this, so only screen 7 pays for it: the
    # frontend calls /api/ai separately once that screen opens.
    #
    # The cheap health probe still runs unconditionally, so the disclosure
    # layer always knows whether a real model is live.
    result["ai"] = (_try_ai_analysis(best, simulation) if include_ai
                    else _ai_status_only())
    result["data_learning"] = _try_data_learning()

    # Computed last, because it reads the finished payload. Everything the
    # project must admit about itself, derived from this run rather than
    # written down somewhere that can go stale.
    try:
        import disclosure
        result["disclosure"] = disclosure.build(result, components)
    except Exception as exc:
        result["disclosure"] = {
            "count": 0, "must_state_count": 0, "must_state": [], "entries": [],
            "error": f"{type(exc).__name__}: {exc}",
        }

    # --- Chart data ---------------------------------------------------------
    result["visualization"] = _visualization(optimisation, simulation)
    result["interactivity"] = _interactivity_bounds(components, result["user_input"])

    result["meta"]["elapsed_seconds"] = round(time.perf_counter() - started, 4)
    result["ok"] = True
    return result


# ---------------------------------------------------------------------------
# On-demand endpoints
# ---------------------------------------------------------------------------
#
# run() is the main pipeline and stays fast. These are the interactive
# queries: they take user input and answer one specific question, so D calls
# them when a screen needs them rather than paying for all of them up front.

def _components(components_csv: str = None) -> list:
    return optimizer.load_components(components_csv or DEFAULT_COMPONENTS_CSV)


def solve_for(unknown: str,
              max_cost: float = None,
              min_efficiency: float = None,
              max_timeline: float = None,
              top_n: int = 5,
              components_csv: str = None) -> dict:
    """
    Inverse solve. Pin what you know, name what you don't.

        solve_for("efficiency", max_cost=150e6, max_timeline=5.0)
        solve_for("cost", min_efficiency=0.65)
        solve_for("timeline", max_cost=170e6, min_efficiency=0.60)
    """
    import solver
    try:
        outcome = solver.solve(_components(components_csv), unknown,
                               max_cost=max_cost,
                               min_efficiency=min_efficiency,
                               max_timeline=max_timeline,
                               top_n=top_n)
        return {"ok": True, **outcome.to_dict()}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def achievable_ranges(components_csv: str = None) -> dict:
    """Hard limits of what any configuration can deliver. Sets slider bounds."""
    import solver
    return solver.achievable_ranges(_components(components_csv))


def tradeoff_frontier(max_points: int = 60, components_csv: str = None) -> dict:
    """Pareto-optimal configurations -- the honest menu of trade-offs."""
    import solver
    return solver.pareto_frontier(_components(components_csv), max_points)


def cost_reduction(target_cost_usd: float = None,
                   exclude_hypothetical: bool = False,
                   min_efficiency: float = None,
                   components_csv: str = None) -> dict:
    """
    "I want it to cost this much -- how do I get there, and what do I lose?"

    Returns every possible component swap ranked by value, plus a concrete
    ordered pathway to the target if one is given.
    """
    import cost_advisor
    try:
        return {"ok": True,
                **cost_advisor.advise(_components(components_csv),
                                      target_cost_usd=target_cost_usd,
                                      exclude_hypothetical=exclude_hypothetical,
                                      min_efficiency=min_efficiency)}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def alternatives_for(category: str, components_csv: str = None) -> dict:
    """Every option in one category, side by side against the baseline."""
    import cost_advisor
    return cost_advisor.alternatives_for(_components(components_csv), category)


def optimize_design(goal: str = "balanced", components_csv: str = None,
                    **constraints) -> dict:
    """
    "Tell me what you want and I'll optimise for it."

    Goals: min_cost, max_efficiency, max_resolution, max_throughput,
           min_timeline, max_domestic, balanced

    Constraints are all optional: budget_usd, min_efficiency,
    max_timeline_years, max_resolution_nm, min_throughput_wph,
    required_countries, excluded_suppliers, exclude_hypothetical.
    """
    import design_optimizer
    try:
        return design_optimizer.optimize_for(
            _components(components_csv), goal=goal, **constraints)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def compare_design_goals(components_csv: str = None, **constraints) -> dict:
    """Best machine for every goal, side by side."""
    import design_optimizer
    return design_optimizer.compare_goals(
        _components(components_csv), **constraints)


def design_goals() -> dict:
    """The goals a user can pick from. For populating a dropdown."""
    import design_optimizer
    return {"goals": design_optimizer.GOALS}


# ---------------------------------------------------------------------------
# Chart shaping -- D renders these directly, no reshaping needed
# ---------------------------------------------------------------------------

def _visualization(optimisation: dict, simulation: dict) -> dict:
    top = optimisation["top_configurations"]
    baseline = optimisation.get("baseline")

    cost_bar = []
    if baseline:
        cost_bar.append({"label": "ASML baseline",
                         "value": baseline["total_cost_usd"],
                         "is_baseline": True})
    for config in top:
        cost_bar.append({"label": f"Option {config['rank']}",
                         "value": config["total_cost_usd"],
                         "is_baseline": False})

    cost_pie = []
    if top:
        for component in top[0]["components"]:
            cost_pie.append({"label": component["category"],
                             "value": component["cost_usd"],
                             "name": component["name"]})

    timeline = []
    if baseline:
        timeline.append({"label": "ASML approach",
                         "years": baseline["timeline_years"]})
    for config in top:
        timeline.append({"label": f"Option {config['rank']}",
                         "years": config["timeline_years"]})

    efficiency = [{"label": f"Option {config['rank']}",
                   "value": config["efficiency_pct"]} for config in top]
    if baseline:
        efficiency.insert(0, {"label": "ASML baseline",
                              "value": round(baseline["overall_efficiency"] * 100.0, 2)})

    return {
        "cost_bar": cost_bar,
        "cost_pie": cost_pie,
        "timeline": timeline,
        "efficiency": efficiency,
        "simulation_stages": simulation.get("stages", []),
        "parts_mapping": optimisation.get("component_mapping", []),
    }


def _interactivity_bounds(components: list, current: dict) -> dict:
    """
    Slider ranges for screen 4.  Derived from the actual data so a judge can
    never drag a slider into a range with no possible answer.
    """
    grouped = optimizer.group_by_category(components)

    cheapest = sum(min(alts, key=lambda c: c.cost_usd).cost_usd
                   for alts in grouped.values())
    priciest = sum(max(alts, key=lambda c: c.cost_usd).cost_usd
                   for alts in grouped.values())

    max_eff = 1.0
    min_eff = 1.0
    for alts in grouped.values():
        max_eff *= max(alt.efficiency for alt in alts)
        min_eff *= min(alt.efficiency for alt in alts)

    fastest = max(min(alt.lead_time_years for alt in alts) for alts in grouped.values())
    slowest = max(max(alt.lead_time_years for alt in alts) for alts in grouped.values())

    return {
        "budget_usd": {"min": round(cheapest, 2), "max": round(priciest, 2),
                       "current": current["budget_usd"], "step": 1_000_000},
        "min_efficiency": {"min": round(min_eff, 4), "max": round(max_eff, 4),
                           "current": current["min_efficiency"], "step": 0.01},
        "max_timeline_years": {"min": round(fastest, 2), "max": round(slowest, 2),
                               "current": current["max_timeline_years"], "step": 0.5},
        "iso_class": {"min": 1, "max": 9, "current": current["iso_class"], "step": 1},
        "dose_mj_cm2": {"min": 10.0, "max": 60.0,
                        "current": current["dose_mj_cm2"], "step": 1.0},
        "categories": sorted(grouped.keys()),
        "countries": sorted({component.country for component in components}),
        "suppliers": sorted({component.supplier for component in components}),
    }


if __name__ == "__main__":
    import json as _json

    outcome = run()
    print(_json.dumps({
        "ok": outcome["ok"],
        "elapsed_seconds": outcome["meta"]["elapsed_seconds"],
        "combinations": outcome["results"]["combinations_evaluated"],
        "feasible": outcome["results"]["feasible_count"],
        "best_cost": outcome["results"]["top_configurations"][0]["total_cost_usd"],
        "savings": outcome["results"]["savings"],
        "resolution_nm": outcome["simulation"]["resolution_nm"],
        "throughput_wph": outcome["simulation"]["throughput_wph"],
        "particle_risk": outcome["particles"]["risk_level"],
        "ai_status": outcome["ai"]["status"],
        "errors": outcome["errors"],
    }, indent=2))
