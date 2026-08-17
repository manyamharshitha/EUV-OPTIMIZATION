"""
cost_advisor.py  --  Person B (Algorithm Engineer)

Cost reduction pathways.

The optimizer tells you what the best machine is. It does not tell you how to
get from the machine you have to a machine you can afford, or what each step
costs you in capability. That is the question a procurement decision actually
turns on, and it is the question this module answers.

Three things it produces:

    swap_options()       every single-component substitution, ranked by how
                         much efficiency each dollar of saving costs you

    reduction_pathway()  a concrete ordered plan from the baseline down to a
                         target cost, cheapest-pain-first

    alternatives_for()   for one category, every option side by side against
                         the baseline part

The ranking metric throughout is *efficiency points lost per million dollars
saved*. Lower is better. A swap that saves money and loses nothing is free;
one that saves little and costs a lot of capability is a trap.

Exhaustive, deterministic, standard library only.
"""

from __future__ import annotations

import optimizer


def _baseline_map(components: list) -> dict:
    """category -> the baseline component for it."""
    return {c.category: c for c in components if c.is_baseline}


def _pain_ratio(efficiency_lost_pct: float, cost_saved_usd: float) -> float | None:
    """
    Efficiency points surrendered per million dollars saved.

    None means the swap saves nothing, so the ratio is meaningless -- those
    are filtered out rather than shown with a fake number.
    """
    if cost_saved_usd <= 0:
        return None
    return efficiency_lost_pct / (cost_saved_usd / 1_000_000.0)


def swap_options(components: list, exclude_hypothetical: bool = False) -> list:
    """
    Every way to replace one baseline component with an alternative.

    Returns them ranked best-value-first: the swaps at the top give up the
    least capability per dollar saved.
    """
    grouped = optimizer.group_by_category(components)
    baselines = _baseline_map(components)

    options = []
    for category, parts in grouped.items():
        base = baselines.get(category)
        if base is None:
            continue

        for part in parts:
            if part.component_id == base.component_id:
                continue
            if exclude_hypothetical and part.supplier.strip().upper() == "HYPOTHETICAL":
                continue

            cost_saved = base.cost_usd - part.cost_usd
            efficiency_lost_pct = (base.efficiency - part.efficiency) * 100.0
            time_delta = part.lead_time_years - base.lead_time_years

            options.append({
                "category": category,
                "from_id": base.component_id,
                "from_name": base.name,
                "from_cost_usd": base.cost_usd,
                "to_id": part.component_id,
                "to_name": part.name,
                "to_cost_usd": part.cost_usd,
                "to_supplier": part.supplier,
                "to_country": part.country,
                "is_hypothetical": part.supplier.strip().upper() == "HYPOTHETICAL",
                "cost_saved_usd": round(cost_saved, 2),
                "cost_saved_pct": round(cost_saved / base.cost_usd * 100, 2)
                if base.cost_usd else 0.0,
                "efficiency_lost_pct": round(efficiency_lost_pct, 3),
                "timeline_delta_years": round(time_delta, 2),
                "pain_ratio": _pain_ratio(efficiency_lost_pct, cost_saved),
                "source": part.source,
                "confidence": part.confidence,
            })

    savers = [o for o in options if o["cost_saved_usd"] > 0]
    others = [o for o in options if o["cost_saved_usd"] <= 0]

    savers.sort(key=lambda o: (o["pain_ratio"], -o["cost_saved_usd"]))
    others.sort(key=lambda o: -o["cost_saved_usd"])

    return savers + others


def reduction_pathway(components: list,
                      target_cost_usd: float,
                      exclude_hypothetical: bool = False,
                      min_efficiency: float | None = None) -> dict:
    """
    A concrete plan: which parts to swap, in what order, to reach a cost
    target, giving up as little capability as possible at each step.

    Greedy on pain ratio. Greedy is not provably optimal here -- but it is
    explainable, and an explainable plan a human can argue with beats an
    opaque one they cannot. `optimizer.optimize()` already does the exhaustive
    search if you want the true optimum; this tells you how to *get there*.
    """
    baselines = _baseline_map(components)
    if not baselines:
        return {"ok": False, "reason": "no baseline components in database"}

    chosen = dict(baselines)

    def totals(selection: dict):
        return optimizer.aggregate(list(selection.values()))

    start_cost, start_efficiency, start_timeline = totals(chosen)

    if start_cost <= target_cost_usd:
        return {
            "ok": True,
            "already_met": True,
            "target_cost_usd": target_cost_usd,
            "baseline_cost_usd": round(start_cost, 2),
            "final_cost_usd": round(start_cost, 2),
            "steps": [],
            "explanation": (
                f"The baseline already costs ${start_cost:,.0f}, which is "
                f"within the ${target_cost_usd:,.0f} target. No changes needed."
            ),
        }

    grouped = optimizer.group_by_category(components)
    steps = []

    while True:
        current_cost, current_efficiency, _ = totals(chosen)
        if current_cost <= target_cost_usd:
            break

        best_move = None
        for category, parts in grouped.items():
            current_part = chosen.get(category)
            if current_part is None:
                continue

            for candidate in parts:
                if candidate.component_id == current_part.component_id:
                    continue
                if (exclude_hypothetical
                        and candidate.supplier.strip().upper() == "HYPOTHETICAL"):
                    continue

                saved = current_part.cost_usd - candidate.cost_usd
                if saved <= 0:
                    continue

                trial = dict(chosen)
                trial[category] = candidate
                _, trial_efficiency, _ = totals(trial)

                if min_efficiency is not None and trial_efficiency < min_efficiency:
                    continue

                lost_pct = (current_efficiency - trial_efficiency) * 100.0
                ratio = _pain_ratio(lost_pct, saved)
                if ratio is None:
                    continue

                if best_move is None or ratio < best_move["pain_ratio"]:
                    best_move = {
                        "category": category,
                        "candidate": candidate,
                        "from_part": current_part,
                        "cost_saved_usd": saved,
                        "efficiency_lost_pct": lost_pct,
                        "pain_ratio": ratio,
                    }

        if best_move is None:
            break

        chosen[best_move["category"]] = best_move["candidate"]
        new_cost, new_efficiency, new_timeline = totals(chosen)

        steps.append({
            "step": len(steps) + 1,
            "category": best_move["category"],
            "replace": best_move["from_part"].name,
            "with": best_move["candidate"].name,
            "supplier": best_move["candidate"].supplier,
            "is_hypothetical":
                best_move["candidate"].supplier.strip().upper() == "HYPOTHETICAL",
            "cost_saved_usd": round(best_move["cost_saved_usd"], 2),
            "efficiency_lost_pct": round(best_move["efficiency_lost_pct"], 3),
            "pain_ratio": round(best_move["pain_ratio"], 4),
            "running_cost_usd": round(new_cost, 2),
            "running_efficiency_pct": round(new_efficiency * 100, 2),
            "running_timeline_years": round(new_timeline, 2),
            "target_met": new_cost <= target_cost_usd,
        })

    final_cost, final_efficiency, final_timeline = totals(chosen)
    reached = final_cost <= target_cost_usd
    hypothetical_steps = sum(1 for s in steps if s["is_hypothetical"])

    if reached:
        explanation = (
            f"Reaching ${target_cost_usd:,.0f} takes {len(steps)} component "
            f"substitution{'s' if len(steps) != 1 else ''}. Cost falls from "
            f"${start_cost:,.0f} to ${final_cost:,.0f}, and efficiency falls "
            f"from {start_efficiency * 100:.2f}% to {final_efficiency * 100:.2f}%."
        )
    else:
        explanation = (
            f"${target_cost_usd:,.0f} is not reachable. The cheapest "
            f"configuration available under these restrictions is "
            f"${final_cost:,.0f}, after {len(steps)} substitutions. "
            f"Every remaining part is already the cheapest option in its "
            f"category."
        )

    if hypothetical_steps:
        explanation += (
            f" {hypothetical_steps} of these steps depend on HYPOTHETICAL "
            f"components that do not exist yet -- this is a development "
            f"roadmap, not a purchase order."
        )

    return {
        "ok": True,
        "already_met": False,
        "target_cost_usd": target_cost_usd,
        "target_reached": reached,
        "baseline_cost_usd": round(start_cost, 2),
        "baseline_efficiency_pct": round(start_efficiency * 100, 2),
        "final_cost_usd": round(final_cost, 2),
        "final_efficiency_pct": round(final_efficiency * 100, 2),
        "final_timeline_years": round(final_timeline, 2),
        "total_saved_usd": round(start_cost - final_cost, 2),
        "total_saved_pct": round((start_cost - final_cost) / start_cost * 100, 2),
        "efficiency_given_up_pct": round(
            (start_efficiency - final_efficiency) * 100, 2),
        "steps_required": len(steps),
        "hypothetical_steps": hypothetical_steps,
        "steps": steps,
        "explanation": explanation,
    }


def alternatives_for(components: list, category: str) -> dict:
    """Every option in one category, side by side against the baseline."""
    grouped = optimizer.group_by_category(components)
    parts = grouped.get(category)
    if not parts:
        return {"ok": False,
                "reason": f"no such category: {category}",
                "available": sorted(grouped)}

    base = _baseline_map(components).get(category)

    rows = []
    for part in sorted(parts, key=lambda p: p.cost_usd):
        row = {
            "component_id": part.component_id,
            "name": part.name,
            "supplier": part.supplier,
            "country": part.country,
            "cost_usd": part.cost_usd,
            "efficiency": part.efficiency,
            "efficiency_pct": round(part.efficiency * 100, 2),
            "lead_time_years": part.lead_time_years,
            "is_baseline": part.is_baseline,
            "is_hypothetical": part.supplier.strip().upper() == "HYPOTHETICAL",
            "source": part.source,
            "confidence": part.confidence,
        }
        if base:
            row["cost_delta_usd"] = round(part.cost_usd - base.cost_usd, 2)
            row["efficiency_delta_pct"] = round(
                (part.efficiency - base.efficiency) * 100, 3)
            row["timeline_delta_years"] = round(
                part.lead_time_years - base.lead_time_years, 2)
        rows.append(row)

    return {
        "ok": True,
        "category": category,
        "baseline_id": base.component_id if base else None,
        "option_count": len(rows),
        "hypothetical_count": sum(1 for r in rows if r["is_hypothetical"]),
        "cheapest_id": rows[0]["component_id"],
        "options": rows,
    }


def advise(components: list,
           target_cost_usd: float | None = None,
           exclude_hypothetical: bool = False,
           min_efficiency: float | None = None) -> dict:
    """Everything the cost-reduction screen needs, in one call."""
    options = swap_options(components, exclude_hypothetical)
    savers = [o for o in options if o["cost_saved_usd"] > 0]

    result = {
        "swap_options": options,
        "best_value_swaps": savers[:5],
        "free_wins": [o for o in savers if o["efficiency_lost_pct"] <= 0],
        "categories": sorted(optimizer.group_by_category(components)),
        "alternatives_by_category": {
            category: alternatives_for(components, category)
            for category in sorted(optimizer.group_by_category(components))
        },
    }

    if target_cost_usd is not None:
        result["pathway"] = reduction_pathway(
            components, target_cost_usd, exclude_hypothetical, min_efficiency)

    return result


if __name__ == "__main__":
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    parts = optimizer.load_components(os.path.join(here, "data", "components.csv"))

    print("=" * 72)
    print("  COST REDUCTION ADVISOR")
    print("=" * 72)

    print("\n  Best-value swaps (least capability lost per $M saved):\n")
    for option in swap_options(parts)[:6]:
        flag = " [HYPOTHETICAL]" if option["is_hypothetical"] else ""
        print(f"    {option['category']:<20} -> {option['to_name'][:34]:<34}{flag}")
        print(f"      saves ${option['cost_saved_usd']:>12,.0f}   "
              f"costs {option['efficiency_lost_pct']:>6.2f} eff pts   "
              f"ratio {option['pain_ratio']:.3f}")

    print("\n" + "-" * 72)
    print("\n  Q: I want to get this machine down to $130M. How?\n")
    plan = reduction_pathway(parts, 130_000_000.0)
    for step in plan["steps"]:
        flag = "  [HYPOTHETICAL]" if step["is_hypothetical"] else ""
        print(f"    {step['step']}. {step['category']}: {step['with'][:40]}{flag}")
        print(f"       -${step['cost_saved_usd']:>12,.0f}  "
              f"-{step['efficiency_lost_pct']:>5.2f} eff  ->  "
              f"${step['running_cost_usd']:,.0f} @ "
              f"{step['running_efficiency_pct']}%")
    print(f"\n  {plan['explanation']}")

    print("\n" + "-" * 72)
    print("\n  Q: Same target, but only real suppliers.\n")
    plan = reduction_pathway(parts, 130_000_000.0, exclude_hypothetical=True)
    print(f"  {plan['explanation']}")
