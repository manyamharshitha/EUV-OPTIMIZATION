"""
design_optimizer.py  --  Person B (Algorithm Engineer)

Goal-driven design optimisation.

`optimizer.py` optimises a fixed weighted score of cost, efficiency and
timeline. That is one question. This module lets the user say what they
actually want -- sharpest resolution, highest throughput, most domestic
content, cheapest machine -- and optimises for that instead, subject to
whatever constraints they impose.

Physics goals (resolution, throughput) require running the simulation for each
candidate. Doing that 19,440 times would be slow, but the simulation depends
only on a handful of spec values, and most configurations share them. So
results are memoised on the spec signature, which collapses the work by
roughly two orders of magnitude.

Exhaustive, deterministic, standard library only.
"""

from __future__ import annotations

import itertools

import euv_simulation
import optimizer


GOALS = {
    "min_cost": "Cheapest machine",
    "max_efficiency": "Highest overall efficiency",
    "max_resolution": "Sharpest printable feature (smallest nm)",
    "max_throughput": "Most wafers per hour",
    "min_timeline": "Fastest to build",
    "max_domestic": "Most domestically sourced content",
    "balanced": "Weighted balance of cost, efficiency and timeline",
}


def _spec_signature(combo) -> tuple:
    """
    The only inputs the simulation actually reads.

    Two configurations with the same signature produce identical physics, so
    the simulation runs once for both.
    """
    specs = {}
    for component in combo:
        specs.update(component.specs or {})

    return (
        specs.get("laser_power_kw", 20.0),
        specs.get("conversion_efficiency", 0.05),
        specs.get("collector_reflectivity", 0.55),
        specs.get("collection_solid_angle_sr", 5.0),
        int(specs.get("mirror_count", 10)),
        specs.get("mirror_reflectivity", 0.70),
        specs.get("numerical_aperture", 0.33),
        specs.get("k1", euv_simulation.DEFAULT_K1),
    )


def _simulate_cached(signature: tuple, dose_mj_cm2: float,
                     target_resolution_nm: float, cache: dict):
    key = signature + (dose_mj_cm2, target_resolution_nm)
    if key not in cache:
        (power, ce, collector_r, solid_angle, mirrors,
         mirror_r, na, k1) = signature
        cache[key] = euv_simulation.run_simulation(
            laser_power_kw=power,
            conversion_efficiency=ce,
            collector_reflectivity=collector_r,
            collection_solid_angle_sr=solid_angle,
            mirror_count=mirrors,
            mirror_reflectivity=mirror_r,
            numerical_aperture=na,
            dose_mj_cm2=dose_mj_cm2,
            k1=k1,
            target_resolution_nm=target_resolution_nm,
        )
    return cache[key]


def _domestic_fraction(combo, home_country: str) -> float:
    """Share of total cost sourced from the home country."""
    total = sum(c.cost_usd for c in combo)
    if total <= 0:
        return 0.0
    home = sum(c.cost_usd for c in combo
               if c.country.strip().lower() == home_country.strip().lower())
    return home / total


def optimize_for(components: list,
                 goal: str = "balanced",
                 budget_usd: float | None = None,
                 min_efficiency: float | None = None,
                 max_timeline_years: float | None = None,
                 max_resolution_nm: float | None = None,
                 min_throughput_wph: float | None = None,
                 required_countries: tuple = (),
                 excluded_suppliers: tuple = (),
                 exclude_hypothetical: bool = False,
                 home_country: str = "India",
                 dose_mj_cm2: float = 20.0,
                 target_resolution_nm: float = 7.0,
                 weights: dict | None = None,
                 top_n: int = 5) -> dict:
    """
    Optimise the design for a stated goal under stated constraints.

    Every constraint is optional. Supplying none means "search everything".
    """
    if goal not in GOALS:
        raise ValueError(f"unknown goal {goal!r}. Valid goals: {sorted(GOALS)}")

    grouped = optimizer.group_by_category(components)
    categories = sorted(grouped)

    # Pre-filter the pools so excluded parts never enter the product at all.
    pools = []
    for category in categories:
        parts = grouped[category]
        if excluded_suppliers:
            excluded = {s.strip().lower() for s in excluded_suppliers}
            parts = [p for p in parts if p.supplier.strip().lower() not in excluded]
        if exclude_hypothetical:
            parts = [p for p in parts
                     if p.supplier.strip().upper() != "HYPOTHETICAL"]
        if not parts:
            return {
                "ok": False,
                "reason": f"every option in category '{category}' was excluded",
                "goal": goal,
            }
        pools.append(parts)

    needs_physics = goal in ("max_resolution", "max_throughput") \
        or max_resolution_nm is not None or min_throughput_wph is not None

    cache: dict = {}
    candidates = []
    evaluated = 0
    rejected = {"budget": 0, "efficiency": 0, "timeline": 0,
                "resolution": 0, "throughput": 0, "country": 0}

    required = {c.strip().lower() for c in required_countries}

    for combo in itertools.product(*pools):
        evaluated += 1
        cost, efficiency, timeline = optimizer.aggregate(list(combo))

        if budget_usd is not None and cost > budget_usd:
            rejected["budget"] += 1
            continue
        if min_efficiency is not None and efficiency < min_efficiency:
            rejected["efficiency"] += 1
            continue
        if max_timeline_years is not None and timeline > max_timeline_years:
            rejected["timeline"] += 1
            continue

        if required:
            present = {c.country.strip().lower() for c in combo}
            if not required.issubset(present):
                rejected["country"] += 1
                continue

        simulation = None
        if needs_physics:
            simulation = _simulate_cached(
                _spec_signature(combo), dose_mj_cm2, target_resolution_nm, cache)

            if (max_resolution_nm is not None
                    and simulation.resolution_nm > max_resolution_nm):
                rejected["resolution"] += 1
                continue
            if (min_throughput_wph is not None
                    and simulation.throughput_wph < min_throughput_wph):
                rejected["throughput"] += 1
                continue

        candidates.append({
            "combo": combo,
            "cost": cost,
            "efficiency": efficiency,
            "timeline": timeline,
            "simulation": simulation,
            "domestic": _domestic_fraction(combo, home_country),
        })

    if not candidates:
        return {
            "ok": False,
            "goal": goal,
            "goal_description": GOALS[goal],
            "reason": "no configuration satisfies these constraints",
            "combinations_evaluated": evaluated,
            "rejected_by": rejected,
            "suggestion": _suggest_relaxation(rejected),
        }

    # Rank by the stated goal. Ties broken by cost so results are stable.
    rankers = {
        "min_cost": lambda c: (c["cost"], -c["efficiency"]),
        "max_efficiency": lambda c: (-c["efficiency"], c["cost"]),
        "min_timeline": lambda c: (c["timeline"], c["cost"]),
        "max_domestic": lambda c: (-c["domestic"], c["cost"]),
        "max_resolution": lambda c: (c["simulation"].resolution_nm, c["cost"]),
        "max_throughput": lambda c: (-c["simulation"].throughput_wph, c["cost"]),
    }

    if goal == "balanced":
        w = weights or {"cost": 0.45, "efficiency": 0.40, "time": 0.15}
        costs = [c["cost"] for c in candidates]
        effs = [c["efficiency"] for c in candidates]
        times = [c["timeline"] for c in candidates]
        lo_c, hi_c = min(costs), max(costs)
        lo_e, hi_e = min(effs), max(effs)
        lo_t, hi_t = min(times), max(times)

        def balanced_score(c):
            return -(
                w["cost"] * optimizer._normalise(c["cost"], lo_c, hi_c, True)
                + w["efficiency"] * optimizer._normalise(
                    c["efficiency"], lo_e, hi_e, False)
                + w["time"] * optimizer._normalise(c["timeline"], lo_t, hi_t, True)
            )

        candidates.sort(key=lambda c: (balanced_score(c), c["cost"]))
    else:
        candidates.sort(key=rankers[goal])

    def render(candidate, rank):
        combo = candidate["combo"]
        simulation = candidate["simulation"]
        if simulation is None:
            simulation = _simulate_cached(
                _spec_signature(combo), dose_mj_cm2, target_resolution_nm, cache)

        return {
            "rank": rank,
            "total_cost_usd": round(candidate["cost"], 2),
            "efficiency_pct": round(candidate["efficiency"] * 100, 2),
            "timeline_years": round(candidate["timeline"], 2),
            "domestic_content_pct": round(candidate["domestic"] * 100, 2),
            "resolution_nm": simulation.resolution_nm,
            "throughput_wph": simulation.throughput_wph,
            "resolution_target_met": simulation.resolution_target_met,
            "hypothetical_parts": sum(
                1 for c in combo if c.supplier.strip().upper() == "HYPOTHETICAL"),
            "components": [
                {
                    "category": c.category,
                    "name": c.name,
                    "supplier": c.supplier,
                    "country": c.country,
                    "cost_usd": c.cost_usd,
                    "is_hypothetical": c.supplier.strip().upper() == "HYPOTHETICAL",
                }
                for c in combo
            ],
        }

    ranked = [render(c, i + 1) for i, c in enumerate(candidates[:top_n])]
    best = ranked[0]

    return {
        "ok": True,
        "goal": goal,
        "goal_description": GOALS[goal],
        "constraints_applied": {
            "budget_usd": budget_usd,
            "min_efficiency": min_efficiency,
            "max_timeline_years": max_timeline_years,
            "max_resolution_nm": max_resolution_nm,
            "min_throughput_wph": min_throughput_wph,
            "required_countries": list(required_countries),
            "excluded_suppliers": list(excluded_suppliers),
            "exclude_hypothetical": exclude_hypothetical,
        },
        "combinations_evaluated": evaluated,
        "feasible_count": len(candidates),
        "rejected_by": rejected,
        "simulations_run": len(cache),
        "best": best,
        "top_configurations": ranked,
        "explanation": (
            f"Optimising for '{GOALS[goal]}' across {evaluated:,} combinations, "
            f"{len(candidates):,} satisfied the constraints. The best delivers "
            f"${best['total_cost_usd']:,.0f}, {best['efficiency_pct']}% "
            f"efficiency, {best['resolution_nm']} nm resolution and "
            f"{best['throughput_wph']} wafers/hour in "
            f"{best['timeline_years']} years."
            + (f" {best['hypothetical_parts']} of its parts are HYPOTHETICAL."
               if best["hypothetical_parts"] else "")
        ),
    }


def _suggest_relaxation(rejected: dict) -> str:
    """Name the constraint that actually did the damage."""
    if not any(rejected.values()):
        return "No candidates were generated at all -- check the component database."

    worst = max(rejected, key=rejected.get)
    labels = {
        "budget": "raise the budget",
        "efficiency": "lower the minimum efficiency",
        "timeline": "allow a longer timeline",
        "resolution": "accept a larger resolution",
        "throughput": "accept lower throughput",
        "country": "drop the required-country requirement",
    }
    return (f"{rejected[worst]:,} configurations failed on {worst} -- "
            f"{labels[worst]} first.")


def compare_goals(components: list, **kwargs) -> dict:
    """
    Optimise for every goal in turn.

    This is the honest answer to "what is the best design?" -- there isn't
    one. Different goals give genuinely different machines, and seeing them
    side by side is more informative than any single ranking.
    """
    kwargs.pop("goal", None)
    kwargs.pop("top_n", None)

    comparison = {}
    for goal in GOALS:
        outcome = optimize_for(components, goal=goal, top_n=1, **kwargs)
        if outcome["ok"]:
            best = outcome["best"]
            comparison[goal] = {
                "description": GOALS[goal],
                "cost_usd": best["total_cost_usd"],
                "efficiency_pct": best["efficiency_pct"],
                "timeline_years": best["timeline_years"],
                "resolution_nm": best["resolution_nm"],
                "throughput_wph": best["throughput_wph"],
                "domestic_content_pct": best["domestic_content_pct"],
                "hypothetical_parts": best["hypothetical_parts"],
            }
        else:
            comparison[goal] = {"description": GOALS[goal],
                                "infeasible": True,
                                "reason": outcome.get("reason")}

    return {
        "goals_compared": len(comparison),
        "comparison": comparison,
        "note": (
            "Each row is the best machine for that single objective. No row "
            "is 'the' answer -- they are different trade-offs, and the choice "
            "between them is a policy decision, not a technical one."
        ),
    }


if __name__ == "__main__":
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    parts = optimizer.load_components(os.path.join(here, "data", "components.csv"))

    print("=" * 78)
    print("  GOAL-DRIVEN DESIGN OPTIMISATION")
    print("=" * 78)
    print("\n  What do you want? Each goal gives a different machine.\n")

    comparison = compare_goals(parts)["comparison"]
    header = (f"    {'goal':<16} {'cost':>14} {'eff':>7} {'res':>8} "
              f"{'wph':>8} {'yrs':>5} {'dom':>6}")
    print(header)
    print("    " + "-" * 70)

    for goal, row in comparison.items():
        if row.get("infeasible"):
            print(f"    {goal:<16} infeasible")
            continue
        print(f"    {goal:<16} ${row['cost_usd']:>13,.0f} "
              f"{row['efficiency_pct']:>6.1f}% {row['resolution_nm']:>7.1f} "
              f"{row['throughput_wph']:>8.0f} {row['timeline_years']:>5.1f} "
              f"{row['domestic_content_pct']:>5.0f}%")

    print("\n" + "-" * 78)
    print("\n  Q: Sharpest resolution, under $200M, no hypothetical parts.\n")
    def report(outcome):
        if outcome["ok"]:
            print(f"  {outcome['explanation']}")
            print(f"  (ran {outcome['simulations_run']} unique simulations for "
                  f"{outcome['combinations_evaluated']:,} combinations)")
        else:
            print(f"  INFEASIBLE: {outcome['reason']}")
            if outcome.get("suggestion"):
                print(f"  {outcome['suggestion']}")

    report(optimize_for(parts, goal="max_resolution", budget_usd=200e6,
                        exclude_hypothetical=True))

    print("\n  Q: Most domestic content, but keep efficiency above 45%.\n")
    report(optimize_for(parts, goal="max_domestic", min_efficiency=0.45))

    print("\n  Q: 150 wafers/hour minimum, cheapest machine that does it.\n")
    report(optimize_for(parts, goal="min_cost", min_throughput_wph=150.0))
