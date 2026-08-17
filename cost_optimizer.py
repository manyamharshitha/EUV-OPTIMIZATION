"""
cost_optimizer.py  --  Person B (Algorithm Engineer)

Cost optimisation against Person A's real handoff data.

Built to the demo specification:

    Cost Comparison            baseline cost vs optimised cost, component by
                               component, total saving displayed
    Alternative Parts          cheaper alternatives for each component, and
                               explicitly which ones do NOT help
    Parts Mapping              which alternative replaces which original
    Top 5 Solutions            ranked, judge can change the budget

Why this module exists separately from `optimizer.py`:

A's file gives cost for 100% of components, efficiency for 13%, and lead time
for none. `optimizer.py` scores on all three and therefore cannot run on A's
data -- the efficiency product collapses to zero. This module scores on what A
actually measured. Every number it produces traces back to a row in her file.

Costs are RANGES, not points. A gave a low and a high for every component
because the true value is not public. This module keeps the range all the way
through to the answer, so the output is "$142M to $310M", not a false
precision like "$187,340,000".

Exhaustive, deterministic, standard library only.
"""

from __future__ import annotations

import itertools
import os

import data_adapter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_HANDOFF = os.path.join(
    os.path.expanduser("~"), "Downloads",
    "components_final_handoff(2) (2).csv")


# ---------------------------------------------------------------------------
# Bill of materials
# ---------------------------------------------------------------------------

def _bom_total(components: list) -> dict:
    """Sum a set of components, carrying the uncertainty range through."""
    low = sum(c["cost_low_usd"] for c in components)
    high = sum(c["cost_high_usd"] for c in components)
    mid = (low + high) / 2.0

    # Report the half-span, so "+/- N%" means what a reader expects. The full
    # span is twice this; reporting the full width next to a "+/-" sign
    # doubles the apparent uncertainty.
    return {
        "cost_low_usd": low,
        "cost_high_usd": high,
        "cost_mid_usd": mid,
        "uncertainty_pct": round((high - low) / 2 / mid * 100, 1) if mid else 0.0,
        "span_pct": round((high - low) / mid * 100, 1) if mid else 0.0,
        "component_count": len(components),
        "research_stage_count": sum(
            1 for c in components if c["readiness_risk"] < 0.6),
        "mean_readiness": round(
            sum(c["readiness_risk"] for c in components) / len(components), 3)
        if components else 0.0,
    }


def baseline_bom(loaded: dict) -> dict:
    """
    A's baseline machine: every row marked Baseline.

    Also reconciles against A's own whole-system benchmark, because the two
    should agree and currently do not.
    """
    components = loaded["components"]
    baseline = [c for c in components if c["is_baseline"]]
    totals = _bom_total(baseline)

    benchmark = next(
        (b for b in loaded["benchmarks"]
         if "conventional" in b["name"].lower()), None)

    reconciliation = None
    if benchmark and benchmark["cost_low_usd"]:
        anchor = benchmark["cost_low_usd"]
        ratio = totals["cost_mid_usd"] / anchor
        inside = totals["cost_low_usd"] <= anchor <= totals["cost_high_usd"]

        reconciliation = {
            "benchmark_id": benchmark["id"],
            "benchmark_name": benchmark["name"],
            "benchmark_usd": anchor,
            "bom_mid_usd": totals["cost_mid_usd"],
            "ratio": round(ratio, 3),
            "anchor_inside_bom_range": inside,
            "verdict": (
                f"The sum of A's baseline allocations "
                f"(${totals['cost_mid_usd']:,.0f} at midpoint) is "
                f"{ratio:.2f}x her own whole-system benchmark of "
                f"${anchor:,.0f}. The benchmark does fall inside the summed "
                f"range ${totals['cost_low_usd']:,.0f}-"
                f"${totals['cost_high_usd']:,.0f}, so the allocations are not "
                f"impossible -- but the midpoints are collectively too high, "
                f"and at least part of that is double counting."
                if inside else
                f"The sum of A's baseline allocations does not contain her own "
                f"benchmark of ${anchor:,.0f}. The allocations need revising."
            ),
        }

    return {
        "components": baseline,
        "totals": totals,
        "reconciliation": reconciliation,
    }


def find_double_counting(loaded: dict) -> list:
    """
    Categories billing more than one Baseline row.

    Two rows marked Baseline in the same category means the machine is being
    charged twice for one function, unless they are genuinely different parts
    that happen to share a component name.
    """
    by_category: dict = {}
    for component in loaded["components"]:
        by_category.setdefault(component["category"], []).append(component)

    findings = []
    for category, parts in sorted(by_category.items()):
        baselines = [p for p in parts if p["is_baseline"]]
        if len(baselines) < 2:
            continue

        extra = sum(b["cost_low_usd"] for b in baselines[1:]), \
            sum(b["cost_high_usd"] for b in baselines[1:])

        findings.append({
            "category": category,
            "baseline_ids": [b["component_id"] for b in baselines],
            "baseline_names": [b["name"] for b in baselines],
            "potential_overcount_low_usd": extra[0],
            "potential_overcount_high_usd": extra[1],
            "question": (
                f"{category} bills {len(baselines)} baseline rows "
                f"({', '.join(b['component_id'] for b in baselines)}). If "
                f"these are the same function listed twice, the machine is "
                f"overcharged by ${extra[0]:,.0f}-${extra[1]:,.0f}."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Alternative parts analysis
# ---------------------------------------------------------------------------

def alternative_analysis(loaded: dict) -> list:
    """
    For every component: which alternatives are cheaper, and which are not.

    The specification asks to show "which alternatives work and which don't".
    An alternative that costs more than the baseline is a real finding, not
    something to hide -- High-NA optics cost more precisely because they do
    more.
    """
    by_category: dict = {}
    for component in loaded["components"]:
        by_category.setdefault(component["category"], []).append(component)

    results = []
    for category, parts in sorted(by_category.items()):
        baselines = [p for p in parts if p["is_baseline"]]
        alternatives = [p for p in parts if not p["is_baseline"]]

        if not alternatives:
            continue

        base = baselines[0] if baselines else None
        rows = []

        for alt in sorted(alternatives, key=lambda p: p["cost_usd"]):
            row = {
                "component_id": alt["component_id"],
                "name": alt["name"],
                "cost_low_usd": alt["cost_low_usd"],
                "cost_high_usd": alt["cost_high_usd"],
                "cost_mid_usd": alt["cost_usd"],
                "readiness": alt["readiness"],
                "readiness_risk": alt["readiness_risk"],
                "efficiency": alt["efficiency"],
                "source": alt["source"],
                "notes": alt["notes"],
            }

            if base:
                saving = base["cost_usd"] - alt["cost_usd"]
                row["saving_mid_usd"] = round(saving, 2)
                row["saving_pct"] = round(saving / base["cost_usd"] * 100, 1) \
                    if base["cost_usd"] else 0.0
                row["cheaper"] = saving > 0
                row["readiness_delta"] = round(
                    alt["readiness_risk"] - base["readiness_risk"], 3)

                if saving > 0 and row["readiness_delta"] >= 0:
                    row["verdict"] = "WORKS -- cheaper, no readiness penalty"
                elif saving > 0:
                    row["verdict"] = (
                        f"TRADE-OFF -- saves ${saving:,.0f} but drops to "
                        f"{alt['readiness']}")
                elif saving < 0:
                    row["verdict"] = (
                        f"COSTS MORE -- ${-saving:,.0f} above baseline; "
                        f"justified only if the capability is needed")
                else:
                    row["verdict"] = "NEUTRAL -- same cost"

            rows.append(row)

        results.append({
            "category": category,
            "baseline_id": base["component_id"] if base else None,
            "baseline_name": base["name"] if base else None,
            "baseline_cost_mid_usd": base["cost_usd"] if base else None,
            "alternatives": rows,
            "cheaper_count": sum(1 for r in rows if r.get("cheaper")),
            "costlier_count": sum(1 for r in rows if r.get("cheaper") is False),
        })

    return results


# ---------------------------------------------------------------------------
# Optimisation
# ---------------------------------------------------------------------------

def optimize(loaded: dict,
             budget_usd: float | None = None,
             min_readiness: float | None = None,
             exclude_research_stage: bool = False,
             top_n: int = 5) -> dict:
    """
    Exhaustive search over every category that offers a choice.

    Categories with a single option are fixed cost -- they are added to every
    configuration but never varied, which is why the combination count is
    1,200 and not larger.
    """
    components = loaded["components"]

    by_category: dict = {}
    for component in components:
        by_category.setdefault(component["category"], []).append(component)

    choosable = {k: v for k, v in sorted(by_category.items()) if len(v) > 1}
    fixed_categories = {k: v[0] for k, v in sorted(by_category.items())
                        if len(v) == 1}
    fixed_parts = list(fixed_categories.values())

    pools = []
    for category, parts in choosable.items():
        usable = parts
        if exclude_research_stage:
            usable = [p for p in parts if p["readiness_risk"] >= 0.6]
        if not usable:
            return {"ok": False,
                    "reason": f"all options in '{category}' were excluded"}
        pools.append(usable)

    candidates = []
    evaluated = 0
    rejected_budget = rejected_readiness = 0

    for combo in itertools.product(*pools):
        evaluated += 1
        selection = list(combo) + fixed_parts
        totals = _bom_total(selection)

        if budget_usd is not None and totals["cost_mid_usd"] > budget_usd:
            rejected_budget += 1
            continue
        if min_readiness is not None and totals["mean_readiness"] < min_readiness:
            rejected_readiness += 1
            continue

        candidates.append({"selection": selection, "chosen": combo,
                           "totals": totals})

    if not candidates:
        return {
            "ok": False,
            "reason": "no configuration satisfies these constraints",
            "combinations_evaluated": evaluated,
            "rejected_by": {"budget": rejected_budget,
                            "readiness": rejected_readiness},
        }

    # Cheapest first; break ties toward higher technology readiness.
    candidates.sort(key=lambda c: (c["totals"]["cost_mid_usd"],
                                   -c["totals"]["mean_readiness"]))

    base = baseline_bom(loaded)
    base_mid = base["totals"]["cost_mid_usd"]

    ranked = []
    for rank, candidate in enumerate(candidates[:top_n], 1):
        totals = candidate["totals"]
        saving = base_mid - totals["cost_mid_usd"]

        ranked.append({
            "rank": rank,
            "cost_low_usd": totals["cost_low_usd"],
            "cost_high_usd": totals["cost_high_usd"],
            "cost_mid_usd": totals["cost_mid_usd"],
            "uncertainty_pct": totals["uncertainty_pct"],
            "saving_vs_baseline_usd": round(saving, 2),
            "saving_pct": round(saving / base_mid * 100, 2) if base_mid else 0.0,
            "mean_readiness": totals["mean_readiness"],
            "research_stage_count": totals["research_stage_count"],
            "chosen": [
                {"category": c["category"], "component_id": c["component_id"],
                 "name": c["name"], "cost_mid_usd": c["cost_usd"],
                 "readiness": c["readiness"], "source": c["source"]}
                for c in candidate["chosen"]
            ],
        })

    return {
        "ok": True,
        "combinations_evaluated": evaluated,
        "feasible_count": len(candidates),
        "rejected_by": {"budget": rejected_budget,
                        "readiness": rejected_readiness},
        "choosable_categories": list(choosable),
        "fixed_categories": list(fixed_categories),
        "fixed_cost_mid_usd": _bom_total(fixed_parts)["cost_mid_usd"],
        "baseline": base["totals"],
        "top_configurations": ranked,
        "best": ranked[0],
    }


def capability_tier(component: dict) -> str:
    """
    Which capability class a part belongs to.

    A's `Projection optics` category holds both 0.33 NA and 0.55 NA High-NA
    parts. Left alone, the optimiser happily "saves" money by swapping a
    High-NA anamorphic optic in for a conventional one -- but those are not
    interchangeable, they print different things. Substitutions that cross a
    tier are flagged rather than silently counted as savings.
    """
    text = f"{component.get('name', '')} {component.get('notes', '')}".lower()

    if "0.55" in text or "high-na" in text or "anamorphic" in text:
        return "high-na"
    if "0.33" in text or "conventional" in text or "full nxe" in text:
        return "low-na"
    return "tier-neutral"


def parts_mapping(loaded: dict, optimized: dict) -> list:
    """Which alternative replaced which original, side by side."""
    if not optimized.get("ok"):
        return []

    baselines = {c["category"]: c for c in loaded["components"]
                 if c["is_baseline"]}

    mapping = []
    for chosen in optimized["best"]["chosen"]:
        original = baselines.get(chosen["category"])
        if original is None:
            continue

        changed = original["component_id"] != chosen["component_id"]
        delta = chosen["cost_mid_usd"] - original["cost_usd"]

        original_tier = capability_tier(original)
        replacement_tier = capability_tier(
            next((c for c in loaded["components"]
                  if c["component_id"] == chosen["component_id"]), chosen))

        crosses_tier = (
            original_tier != replacement_tier
            and "tier-neutral" not in (original_tier, replacement_tier))

        mapping.append({
            "original_tier": original_tier,
            "replacement_tier": replacement_tier,
            "crosses_capability_tier": crosses_tier,
            "validity_warning": (
                f"{original_tier} -> {replacement_tier}: these are not "
                f"like-for-like parts. The 'saving' is not a saving, it is a "
                f"different machine."
                if crosses_tier else None),
            "category": chosen["category"],
            "original_id": original["component_id"],
            "original_name": original["name"],
            "original_cost_mid_usd": original["cost_usd"],
            "replacement_id": chosen["component_id"],
            "replacement_name": chosen["name"],
            "replacement_cost_mid_usd": chosen["cost_mid_usd"],
            "changed": changed,
            "cost_delta_usd": round(delta, 2),
            "saving_usd": round(-delta, 2) if delta < 0 else 0.0,
            "readiness": chosen["readiness"],
        })

    return mapping


def cost_comparison(loaded: dict, optimized: dict) -> dict:
    """The Cost Comparison screen: benchmark, baseline BOM, optimised."""
    base = baseline_bom(loaded)
    rows = []

    for benchmark in loaded["benchmarks"]:
        if not benchmark["cost_low_usd"]:
            continue
        rows.append({
            "label": benchmark["name"],
            "kind": "published benchmark",
            "cost_low_usd": benchmark["cost_low_usd"],
            "cost_high_usd": benchmark["cost_high_usd"],
            "source": benchmark["source"],
        })

    rows.append({
        "label": "A's baseline bill of materials",
        "kind": "modelled allocation",
        "cost_low_usd": base["totals"]["cost_low_usd"],
        "cost_high_usd": base["totals"]["cost_high_usd"],
        "source": "sum of Baseline rows in A's handoff",
    })

    if optimized.get("ok"):
        best = optimized["best"]
        rows.append({
            "label": "Optimised configuration",
            "kind": "computed",
            "cost_low_usd": best["cost_low_usd"],
            "cost_high_usd": best["cost_high_usd"],
            "source": "cost_optimizer.optimize()",
        })

    return {
        "rows": rows,
        "reconciliation": base["reconciliation"],
        "double_counting": find_double_counting(loaded),
        "honesty_note": (
            "Every cost here is a RANGE because no public bill of materials "
            "exists for an EUV scanner. The whole-system benchmarks are "
            "published; the component allocations are modelled by Person A. "
            "Do not present any single figure as a price."
        ),
    }


def run(handoff_path: str = DEFAULT_HANDOFF, **kwargs) -> dict:
    """One call for the whole cost-optimisation screen set."""
    loaded = data_adapter.load_handoff(handoff_path)
    optimized = optimize(loaded, **kwargs)

    return {
        "ok": optimized.get("ok", False),
        "source_file": handoff_path,
        "coverage": data_adapter.analyse(loaded),
        "baseline": baseline_bom(loaded),
        "optimization": optimized,
        "parts_mapping": parts_mapping(loaded, optimized),
        "cost_comparison": cost_comparison(loaded, optimized),
        "alternatives": alternative_analysis(loaded),
    }


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HANDOFF
    result = run(path)

    print("=" * 74)
    print("  COST OPTIMISATION -- Person A's real data")
    print("=" * 74)

    comparison = result["cost_comparison"]
    print("\n  COST COMPARISON\n")
    for row in comparison["rows"]:
        span = (f"${row['cost_low_usd']:,.0f}" if
                row["cost_low_usd"] == row["cost_high_usd"] else
                f"${row['cost_low_usd']:,.0f} - ${row['cost_high_usd']:,.0f}")
        print(f"    {row['label'][:38]:<38} {span:>30}")
        print(f"      {row['kind']}")

    if comparison["reconciliation"]:
        print(f"\n  RECONCILIATION")
        print(f"    {comparison['reconciliation']['verdict']}")

    if comparison["double_counting"]:
        print(f"\n  POSSIBLE DOUBLE COUNTING")
        for finding in comparison["double_counting"]:
            print(f"    {finding['question']}")

    opt = result["optimization"]
    if opt["ok"]:
        best = opt["best"]
        print(f"\n  OPTIMISATION")
        print(f"    evaluated {opt['combinations_evaluated']:,} combinations "
              f"across {len(opt['choosable_categories'])} choosable categories")
        print(f"    {len(opt['fixed_categories'])} categories have one option "
              f"(fixed ${opt['fixed_cost_mid_usd']:,.0f})")
        print(f"\n    best: ${best['cost_low_usd']:,.0f} - "
              f"${best['cost_high_usd']:,.0f} "
              f"(mid ${best['cost_mid_usd']:,.0f})")
        print(f"    saving vs baseline: ${best['saving_vs_baseline_usd']:,.0f} "
              f"({best['saving_pct']}%)")
        print(f"    research-stage parts: {best['research_stage_count']}")

        print(f"\n  TOP {len(opt['top_configurations'])}\n")
        for config in opt["top_configurations"]:
            print(f"    {config['rank']}. ${config['cost_mid_usd']:>14,.0f}  "
                  f"+/-{config['uncertainty_pct']:>5.1f}%  "
                  f"readiness {config['mean_readiness']:.2f}  "
                  f"saves {config['saving_pct']:>5.1f}%")

        print(f"\n  PARTS MAPPING\n")
        for row in result["parts_mapping"]:
            if not row["changed"]:
                continue
            print(f"    {row['category']}")
            print(f"      {row['original_name'][:44]:<44} "
                  f"${row['original_cost_mid_usd']:>13,.0f}")
            print(f"   -> {row['replacement_name'][:44]:<44} "
                  f"${row['replacement_cost_mid_usd']:>13,.0f}")
            print(f"      saves ${row['saving_usd']:,.0f}   "
                  f"({row['readiness']})")

    print(f"\n  ALTERNATIVES -- which work, which do not\n")
    for group in result["alternatives"]:
        print(f"    {group['category']} "
              f"(baseline: {group['baseline_name'][:34] if group['baseline_name'] else 'none'})")
        for alt in group["alternatives"]:
            print(f"      {alt['name'][:40]:<40} {alt.get('verdict', '')[:44]}")
        print()
