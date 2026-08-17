"""
optimizer.py  --  Person B (Algorithm Engineer)

Exhaustive combinatorial optimiser over the EUV bill of materials.

The claim this module has to survive under questioning is "we check ALL
combinations", so it does exactly that -- a full Cartesian product over the
alternatives in every category, with no sampling, no heuristic pruning and no
early exit.  The number of combinations evaluated is reported in the result so
it can be stated out loud and verified.

Reads components.csv (Person A's file).  Never writes it.
Pure standard library -- csv, json, itertools, math.

components.csv schema
---------------------
    component_id      unique string
    category          grouping key; one component is chosen per category
    name              display name
    supplier          vendor
    country           country of origin (sovereignty argument)
    cost_usd          float
    efficiency        float 0..1, performance relative to best-in-class
    lead_time_years   float
    is_baseline       1 for the ASML reference part, 0 otherwise
    specs_json        JSON object of physics parameters for euv_simulation
    source            citation, or the literal string MODELED
    confidence        HIGH | MEDIUM | LOW
"""

from __future__ import annotations

import csv
import json
import math
import os
from dataclasses import dataclass, asdict, field
from itertools import product

# Refuse to start a search that cannot finish inside a live demo.
MAX_COMBINATIONS = 5_000_000

DEFAULT_WEIGHTS = {"cost": 0.45, "efficiency": 0.40, "time": 0.15}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Component:
    component_id: str
    category: str
    name: str
    supplier: str
    country: str
    cost_usd: float
    efficiency: float
    lead_time_years: float
    is_baseline: bool
    specs: dict = field(default_factory=dict, compare=False)
    source: str = "MODELED"
    confidence: str = "LOW"

    @property
    def is_sourced(self) -> bool:
        return self.source.strip().upper() != "MODELED" and bool(self.source.strip())

    def to_dict(self) -> dict:
        data = asdict(self)
        data["is_sourced"] = self.is_sourced
        return data


@dataclass
class Configuration:
    """One complete machine: exactly one component per category."""

    components: list
    total_cost_usd: float
    overall_efficiency: float
    timeline_years: float
    score: float
    rank: int = 0
    feasible: bool = True
    violations: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "score": round(self.score, 6),
            "total_cost_usd": round(self.total_cost_usd, 2),
            "overall_efficiency": round(self.overall_efficiency, 6),
            "efficiency_pct": round(self.overall_efficiency * 100.0, 2),
            "timeline_years": round(self.timeline_years, 2),
            "feasible": self.feasible,
            "violations": list(self.violations),
            "components": [component.to_dict() for component in self.components],
        }


@dataclass
class Constraints:
    max_budget_usd: float = math.inf
    min_efficiency: float = 0.0
    max_timeline_years: float = math.inf
    required_countries: tuple = ()      # sovereignty filter, empty = no filter
    excluded_suppliers: tuple = ()

    def check(self, config_cost: float, config_eff: float, config_time: float,
              components: list) -> list:
        """Return a list of violation strings.  Empty list means feasible."""
        violations = []

        if config_cost > self.max_budget_usd:
            over = config_cost - self.max_budget_usd
            violations.append(f"Over budget by ${over:,.0f}")

        if config_eff < self.min_efficiency:
            violations.append(
                f"Efficiency {config_eff * 100:.1f}% below required "
                f"{self.min_efficiency * 100:.1f}%"
            )

        if config_time > self.max_timeline_years:
            violations.append(
                f"Timeline {config_time:.1f}y exceeds limit "
                f"{self.max_timeline_years:.1f}y"
            )

        if self.required_countries:
            allowed = {country.strip().lower() for country in self.required_countries}
            for component in components:
                if component.country.strip().lower() not in allowed:
                    violations.append(
                        f"{component.name} sourced from {component.country}, "
                        f"outside permitted origins"
                    )
                    break

        if self.excluded_suppliers:
            blocked = {supplier.strip().lower() for supplier in self.excluded_suppliers}
            for component in components:
                if component.supplier.strip().lower() in blocked:
                    violations.append(f"{component.supplier} is an excluded supplier")
                    break

        return violations


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _parse_float(raw: str, default: float = 0.0) -> float:
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return default


def load_components(path: str = "components.csv") -> list:
    """
    Read Person A's component database.

    Rows that cannot be parsed are skipped rather than crashing the demo, but
    a malformed file with zero usable rows raises -- silently optimising over
    nothing would be worse than failing loudly.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"components.csv not found at '{path}'. This is Person A's "
            f"deliverable (handoff A -> B, end of Day 1)."
        )

    components = []
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row.get("component_id") or not row.get("category"):
                continue

            raw_specs = (row.get("specs_json") or "").strip()
            try:
                specs = json.loads(raw_specs) if raw_specs else {}
            except json.JSONDecodeError:
                specs = {}

            components.append(Component(
                component_id=row["component_id"].strip(),
                category=row["category"].strip(),
                name=(row.get("name") or row["component_id"]).strip(),
                supplier=(row.get("supplier") or "Unknown").strip(),
                country=(row.get("country") or "Unknown").strip(),
                cost_usd=_parse_float(row.get("cost_usd")),
                efficiency=min(max(_parse_float(row.get("efficiency")), 0.0), 1.0),
                lead_time_years=_parse_float(row.get("lead_time_years")),
                is_baseline=str(row.get("is_baseline", "0")).strip() in ("1", "true", "True"),
                specs=specs,
                source=(row.get("source") or "MODELED").strip(),
                confidence=(row.get("confidence") or "LOW").strip().upper(),
            ))

    if not components:
        raise ValueError(f"No usable rows in '{path}'.")

    return components


def group_by_category(components: list) -> dict:
    """Ordered mapping category -> list of alternatives."""
    grouped = {}
    for component in components:
        grouped.setdefault(component.category, []).append(component)
    return grouped


def count_combinations(grouped: dict) -> int:
    total = 1
    for alternatives in grouped.values():
        total *= len(alternatives)
    return total


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(components: list) -> tuple:
    """
    Collapse a chosen set of components into (cost, efficiency, timeline).

    Cost is additive.
    Efficiency is MULTIPLICATIVE -- the machine is a chain, and a chain of
    optical elements loses at every stage.  Averaging would let one excellent
    component hide a catastrophic one, which is precisely the mistake this
    project is arguing against.
    Timeline is the MAXIMUM lead time -- procurement runs in parallel, so the
    slowest part sets the schedule.
    """
    total_cost = 0.0
    efficiency = 1.0
    timeline = 0.0

    for component in components:
        total_cost += component.cost_usd
        efficiency *= component.efficiency
        timeline = max(timeline, component.lead_time_years)

    return total_cost, efficiency, timeline


def _normalise(value: float, low: float, high: float, lower_is_better: bool) -> float:
    """Map value into 0..1 where 1 is always better."""
    if high <= low:
        return 1.0
    fraction = (value - low) / (high - low)
    return 1.0 - fraction if lower_is_better else fraction


def score_configuration(cost: float, efficiency: float, timeline: float,
                        bounds: dict, weights: dict) -> float:
    """Weighted sum of normalised cost, efficiency and timeline. Higher is better."""
    cost_score = _normalise(cost, bounds["cost_min"], bounds["cost_max"], True)
    eff_score = _normalise(efficiency, bounds["eff_min"], bounds["eff_max"], False)
    time_score = _normalise(timeline, bounds["time_min"], bounds["time_max"], True)

    return (weights["cost"] * cost_score
            + weights["efficiency"] * eff_score
            + weights["time"] * time_score)


# ---------------------------------------------------------------------------
# The search
# ---------------------------------------------------------------------------

def optimize(components: list,
             constraints: Constraints = None,
             weights: dict = None,
             top_n: int = 5) -> dict:
    """
    Evaluate every combination, keep the feasible ones, rank them, return the
    best `top_n`.

    Two passes are required because scoring needs population-wide min/max to
    normalise against, and those are not known until every combination has
    been costed.  The first pass is arithmetic only, so it is cheap.
    """
    constraints = constraints or Constraints()
    weights = weights or DEFAULT_WEIGHTS

    grouped = group_by_category(components)
    categories = sorted(grouped.keys())
    total_combinations = count_combinations(grouped)

    if total_combinations > MAX_COMBINATIONS:
        raise ValueError(
            f"{total_combinations:,} combinations exceeds the {MAX_COMBINATIONS:,} "
            f"limit. Reduce alternatives per category."
        )

    alternatives = [grouped[category] for category in categories]

    # Pass 1 -- evaluate and filter.
    evaluated = []
    infeasible_count = 0

    for chosen in product(*alternatives):
        chosen = list(chosen)
        cost, efficiency, timeline = aggregate(chosen)
        violations = constraints.check(cost, efficiency, timeline, chosen)

        if violations:
            infeasible_count += 1
            continue

        evaluated.append((chosen, cost, efficiency, timeline))

    result = {
        "categories": categories,
        "combinations_evaluated": total_combinations,
        "feasible_count": len(evaluated),
        "infeasible_count": infeasible_count,
        "weights": dict(weights),
        "top_configurations": [],
        "baseline": None,
        "savings": None,
    }

    if not evaluated:
        result["message"] = (
            "No configuration satisfies these constraints. "
            "Raise the budget, lower the efficiency floor, or extend the timeline."
        )
        return result

    costs = [row[1] for row in evaluated]
    effs = [row[2] for row in evaluated]
    times = [row[3] for row in evaluated]

    bounds = {
        "cost_min": min(costs), "cost_max": max(costs),
        "eff_min": min(effs), "eff_max": max(effs),
        "time_min": min(times), "time_max": max(times),
    }

    # Pass 2 -- score.
    scored = []
    for chosen, cost, efficiency, timeline in evaluated:
        score = score_configuration(cost, efficiency, timeline, bounds, weights)
        scored.append(Configuration(
            components=chosen,
            total_cost_usd=cost,
            overall_efficiency=efficiency,
            timeline_years=timeline,
            score=score,
        ))

    # Deterministic ordering: score desc, then cost asc, then component ids.
    scored.sort(key=lambda config: (
        -config.score,
        config.total_cost_usd,
        tuple(component.component_id for component in config.components),
    ))

    top = scored[:top_n]
    for index, config in enumerate(top, start=1):
        config.rank = index

    result["top_configurations"] = [config.to_dict() for config in top]

    baseline = build_baseline(components)
    if baseline is not None:
        result["baseline"] = baseline.to_dict()
        best = top[0]
        saving = baseline.total_cost_usd - best.total_cost_usd
        result["savings"] = {
            "absolute_usd": round(saving, 2),
            "percent": round((saving / baseline.total_cost_usd * 100.0), 2)
                       if baseline.total_cost_usd else 0.0,
            "efficiency_delta_pct": round(
                (best.overall_efficiency - baseline.overall_efficiency) * 100.0, 3),
            "timeline_delta_years": round(
                best.timeline_years - baseline.timeline_years, 2),
        }
        result["component_mapping"] = build_mapping(baseline, best)

    return result


def build_baseline(components: list):
    """
    The ASML reference machine: the components flagged is_baseline.
    Returns None if Person A has not flagged any.
    """
    grouped = group_by_category(components)
    chosen = []

    for category in sorted(grouped.keys()):
        baseline_parts = [c for c in grouped[category] if c.is_baseline]
        if not baseline_parts:
            return None
        chosen.append(baseline_parts[0])

    cost, efficiency, timeline = aggregate(chosen)
    return Configuration(
        components=chosen,
        total_cost_usd=cost,
        overall_efficiency=efficiency,
        timeline_years=timeline,
        score=0.0,
        rank=0,
    )


def build_mapping(baseline: Configuration, optimized: Configuration) -> list:
    """
    Part-for-part replacement table: which alternative replaces which original.
    Feeds the Parts Mapping screen.
    """
    baseline_by_category = {c.category: c for c in baseline.components}
    rows = []

    for component in optimized.components:
        original = baseline_by_category.get(component.category)
        if original is None:
            continue

        saving = original.cost_usd - component.cost_usd
        rows.append({
            "category": component.category,
            "original_name": original.name,
            "original_supplier": original.supplier,
            "original_country": original.country,
            "original_cost_usd": round(original.cost_usd, 2),
            "replacement_name": component.name,
            "replacement_supplier": component.supplier,
            "replacement_country": component.country,
            "replacement_cost_usd": round(component.cost_usd, 2),
            "changed": original.component_id != component.component_id,
            "saving_usd": round(saving, 2),
            "saving_pct": round(saving / original.cost_usd * 100.0, 2)
                          if original.cost_usd else 0.0,
            "efficiency_delta": round(component.efficiency - original.efficiency, 4),
            "source": component.source,
            "confidence": component.confidence,
        })

    rows.sort(key=lambda row: row["saving_usd"], reverse=True)
    return rows


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "sample_data/components.csv"
    parts = load_components(path)
    grouped = group_by_category(parts)

    print(f"Loaded {len(parts)} components across {len(grouped)} categories")
    print(f"Search space: {count_combinations(grouped):,} combinations\n")

    outcome = optimize(parts, Constraints(max_budget_usd=180_000_000))

    print(f"Evaluated : {outcome['combinations_evaluated']:,}")
    print(f"Feasible  : {outcome['feasible_count']:,}\n")

    for config in outcome["top_configurations"]:
        print(f"#{config['rank']}  ${config['total_cost_usd']:>14,.0f}   "
              f"eff {config['efficiency_pct']:>5.2f}%   "
              f"{config['timeline_years']:>4.1f}y   score {config['score']:.4f}")
