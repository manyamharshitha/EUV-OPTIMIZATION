"""
solver.py  --  Person B (Algorithm Engineer)

Inverse solving.

`optimizer.py` answers the forward question: "here are my limits on cost,
efficiency and time -- what is feasible?"

That is not how anyone actually thinks about a machine. A real question is
"I have 150 million and five years. What efficiency can I actually get?" or
"I need 60% efficiency in four years. What will that cost me?"

This module answers any of those. You pin the variables you know and name the
one you do not, and it returns the achievable value plus the configuration
that delivers it.

It also computes the Pareto frontier -- the set of configurations where you
cannot improve one objective without giving up another. That is the honest
answer to "what are my options", because everything not on the frontier is
strictly worse than something that is.

Exhaustive, deterministic, standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass

import optimizer


SOLVABLE = ("cost", "efficiency", "timeline")


@dataclass
class SolveResult:
    """What the unknown variable can be, given everything else."""

    solved_for: str
    achievable: float | None
    direction: str
    known: dict
    configuration: dict | None
    feasible_count: int
    combinations_evaluated: int
    explanation: str
    alternatives: list

    def to_dict(self) -> dict:
        return {
            "solved_for": self.solved_for,
            "achievable": self.achievable,
            "direction": self.direction,
            "known": self.known,
            "configuration": self.configuration,
            "feasible_count": self.feasible_count,
            "combinations_evaluated": self.combinations_evaluated,
            "explanation": self.explanation,
            "alternatives": self.alternatives,
        }


def _enumerate(components: list):
    """
    Every configuration, with its three objectives. One pass, reused by every
    query in this module so we never pay for the cartesian product twice.
    """
    import itertools

    grouped = optimizer.group_by_category(components)
    categories = sorted(grouped)
    pools = [grouped[c] for c in categories]

    rows = []
    for combo in itertools.product(*pools):
        cost, efficiency, timeline = optimizer.aggregate(list(combo))
        rows.append({
            "cost": cost,
            "efficiency": efficiency,
            "timeline": timeline,
            "components": combo,
        })
    return rows, categories


def _describe(combo) -> dict:
    """Turn a component tuple into the display shape backend.py already uses."""
    cost, efficiency, timeline = optimizer.aggregate(list(combo))
    return {
        "total_cost_usd": round(cost, 2),
        "overall_efficiency": round(efficiency, 6),
        "efficiency_pct": round(efficiency * 100, 2),
        "timeline_years": round(timeline, 2),
        "components": [
            {
                "component_id": c.component_id,
                "category": c.category,
                "name": c.name,
                "supplier": c.supplier,
                "country": c.country,
                "cost_usd": c.cost_usd,
                "efficiency": c.efficiency,
                "lead_time_years": c.lead_time_years,
                "specs": c.specs,
                "source": c.source,
                "confidence": c.confidence,
                "is_hypothetical": c.supplier.strip().upper() == "HYPOTHETICAL",
            }
            for c in combo
        ],
    }


def solve(components: list,
          solve_for: str,
          max_cost: float | None = None,
          min_efficiency: float | None = None,
          max_timeline: float | None = None,
          top_n: int = 5) -> SolveResult:
    """
    Solve for one unknown given any combination of the others.

        solve(components, "efficiency", max_cost=150e6, max_timeline=5.0)
            -> the best efficiency reachable inside 150M and 5 years

        solve(components, "cost", min_efficiency=0.60, max_timeline=4.0)
            -> the cheapest machine hitting 60% within 4 years

        solve(components, "timeline", max_cost=160e6, min_efficiency=0.55)
            -> the fastest route to 55% efficiency under 160M

    Pass only the constraints you actually have. Leaving one out means
    "unconstrained", not "zero".
    """
    if solve_for not in SOLVABLE:
        raise ValueError(f"solve_for must be one of {SOLVABLE}, got {solve_for!r}")

    rows, _ = _enumerate(components)
    total = len(rows)

    # Apply only the constraints the caller supplied, and never constrain the
    # variable being solved for.
    def satisfies(row) -> bool:
        if solve_for != "cost" and max_cost is not None and row["cost"] > max_cost:
            return False
        if (solve_for != "efficiency" and min_efficiency is not None
                and row["efficiency"] < min_efficiency):
            return False
        if (solve_for != "timeline" and max_timeline is not None
                and row["timeline"] > max_timeline):
            return False
        return True

    feasible = [r for r in rows if satisfies(r)]

    known = {}
    if max_cost is not None and solve_for != "cost":
        known["max_cost_usd"] = max_cost
    if min_efficiency is not None and solve_for != "efficiency":
        known["min_efficiency"] = min_efficiency
    if max_timeline is not None and solve_for != "timeline":
        known["max_timeline_years"] = max_timeline

    if not feasible:
        return SolveResult(
            solved_for=solve_for,
            achievable=None,
            direction="none",
            known=known,
            configuration=None,
            feasible_count=0,
            combinations_evaluated=total,
            explanation=(
                "No configuration satisfies those constraints. Relax one of "
                "them -- the solver checked every one of "
                f"{total:,} combinations and none qualified."
            ),
            alternatives=[],
        )

    # Optimise the unknown in its natural direction.
    if solve_for == "efficiency":
        feasible.sort(key=lambda r: (-r["efficiency"], r["cost"], r["timeline"]))
        best = feasible[0]
        achievable = round(best["efficiency"], 6)
        direction = "maximum"
        readable = f"{achievable * 100:.2f}% efficiency"
    elif solve_for == "cost":
        feasible.sort(key=lambda r: (r["cost"], -r["efficiency"], r["timeline"]))
        best = feasible[0]
        achievable = round(best["cost"], 2)
        direction = "minimum"
        readable = f"${achievable:,.0f}"
    else:
        feasible.sort(key=lambda r: (r["timeline"], r["cost"], -r["efficiency"]))
        best = feasible[0]
        achievable = round(best["timeline"], 2)
        direction = "minimum"
        readable = f"{achievable} years"

    constraint_text = ", ".join(f"{k} = {v:,}" for k, v in known.items()) \
        or "no constraints"

    return SolveResult(
        solved_for=solve_for,
        achievable=achievable,
        direction=direction,
        known=known,
        configuration=_describe(best["components"]),
        feasible_count=len(feasible),
        combinations_evaluated=total,
        explanation=(
            f"Given {constraint_text}, the {direction} achievable "
            f"{solve_for} is {readable}. "
            f"{len(feasible):,} of {total:,} combinations satisfied the "
            f"constraints; this is the best of them."
        ),
        alternatives=[_describe(r["components"]) for r in feasible[1:top_n + 1]],
    )


def pareto_frontier(components: list, max_points: int = 60) -> dict:
    """
    Configurations where nothing else is better on every axis at once.

    Cheaper, more efficient, faster -- you can have any two. This returns the
    honest menu of trade-offs rather than a single "optimal" answer that
    depends on weights someone chose arbitrarily.
    """
    rows, _ = _enumerate(components)

    def dominates(a, b) -> bool:
        """a beats b on every axis, and strictly on at least one."""
        return (a["cost"] <= b["cost"]
                and a["efficiency"] >= b["efficiency"]
                and a["timeline"] <= b["timeline"]
                and (a["cost"] < b["cost"]
                     or a["efficiency"] > b["efficiency"]
                     or a["timeline"] < b["timeline"]))

    # Sort by cost so we can prune: only configurations seen so far can
    # dominate the current one on cost.
    rows.sort(key=lambda r: (r["cost"], -r["efficiency"], r["timeline"]))

    frontier = []
    for row in rows:
        if not any(dominates(kept, row) for kept in frontier):
            frontier = [k for k in frontier if not dominates(row, k)]
            frontier.append(row)

    frontier.sort(key=lambda r: r["cost"])

    # Thin evenly if the frontier is large, keeping both extremes.
    shown = frontier
    if len(frontier) > max_points:
        step = len(frontier) / max_points
        shown = [frontier[int(i * step)] for i in range(max_points)]
        shown[-1] = frontier[-1]

    return {
        "frontier_size": len(frontier),
        "combinations_evaluated": len(rows),
        "returned": len(shown),
        "explanation": (
            f"{len(frontier):,} configurations are Pareto-optimal out of "
            f"{len(rows):,}. For every one of the other "
            f"{len(rows) - len(frontier):,}, some configuration on this "
            f"frontier is better on cost, efficiency and timeline "
            f"simultaneously -- there is no reason to ever pick them."
        ),
        "points": [
            {
                "cost_usd": round(r["cost"], 2),
                "efficiency_pct": round(r["efficiency"] * 100, 2),
                "timeline_years": round(r["timeline"], 2),
            }
            for r in shown
        ],
        "cheapest": _describe(frontier[0]["components"]),
        "most_efficient": _describe(
            max(frontier, key=lambda r: r["efficiency"])["components"]),
        "fastest": _describe(
            min(frontier, key=lambda r: r["timeline"])["components"]),
    }


def achievable_ranges(components: list) -> dict:
    """
    The absolute envelope: what is possible at all, ignoring preferences.

    Used to set honest slider bounds so the UI cannot ask for something no
    configuration can deliver.
    """
    rows, _ = _enumerate(components)

    costs = [r["cost"] for r in rows]
    efficiencies = [r["efficiency"] for r in rows]
    timelines = [r["timeline"] for r in rows]

    return {
        "cost_usd": {"min": round(min(costs), 2), "max": round(max(costs), 2)},
        "efficiency_pct": {"min": round(min(efficiencies) * 100, 2),
                           "max": round(max(efficiencies) * 100, 2)},
        "timeline_years": {"min": round(min(timelines), 2),
                           "max": round(max(timelines), 2)},
        "combinations": len(rows),
        "note": (
            "These are hard limits from the component database. A request "
            "outside them is impossible, not merely expensive."
        ),
    }


if __name__ == "__main__":
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    parts = optimizer.load_components(os.path.join(here, "data", "components.csv"))

    print("=" * 66)
    print("  INVERSE SOLVER")
    print("=" * 66)

    print("\n  Q: I have $150M and 5 years. What efficiency can I get?")
    answer = solve(parts, "efficiency", max_cost=150e6, max_timeline=5.0)
    print(f"  A: {answer.explanation}")

    print("\n  Q: I need 65% efficiency within 6 years. What does it cost?")
    answer = solve(parts, "cost", min_efficiency=0.65, max_timeline=6.0)
    print(f"  A: {answer.explanation}")

    print("\n  Q: I need 60% efficiency under $170M. How fast?")
    answer = solve(parts, "timeline", min_efficiency=0.60, max_cost=170e6)
    print(f"  A: {answer.explanation}")

    print("\n" + "-" * 66)
    frontier = pareto_frontier(parts)
    print(f"  {frontier['explanation']}")
    print(f"\n  cheapest       : ${frontier['cheapest']['total_cost_usd']:,.0f} "
          f"at {frontier['cheapest']['efficiency_pct']}%")
    print(f"  most efficient : ${frontier['most_efficient']['total_cost_usd']:,.0f} "
          f"at {frontier['most_efficient']['efficiency_pct']}%")

    print("\n" + "-" * 66)
    ranges = achievable_ranges(parts)
    print(f"  cost      : ${ranges['cost_usd']['min']:,.0f} "
          f"to ${ranges['cost_usd']['max']:,.0f}")
    print(f"  efficiency: {ranges['efficiency_pct']['min']}% "
          f"to {ranges['efficiency_pct']['max']}%")
    print(f"  timeline  : {ranges['timeline_years']['min']} "
          f"to {ranges['timeline_years']['max']} years")
