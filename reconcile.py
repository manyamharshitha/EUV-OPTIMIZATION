"""
reconcile.py  --  making A's bill of materials add up

Person A's baseline rows sum to $294.75M at midpoint. A's own whole-system
benchmark, from the same file, is $200M. A 1.47x gap between two numbers in
one spreadsheet is the kind of thing a judge finds by adding up the column
you put on screen.

The gap is not sloppiness. It comes from a real modelling problem: A built
the database by walking public descriptions of an EUV scanner, and those
descriptions name the same hardware at several levels of abstraction. "EUV
light source", "drive laser", and "dual-pulse CO2 architecture" are three
ways of describing overlapping things. Priced as three line items, the
machine gets charged three times.

This module classifies every baseline row against three questions:

    Is it a PARENT of other rows already counted?
    Is it a DUPLICATE of another row?
    Is it an ATTRIBUTE of hardware already counted, rather than hardware?

and produces a reconciled bill of materials plus the reasoning for each
exclusion, so A can accept or reject them individually.

Every judgement here is ours, not A's. They are flagged NEEDS_A_CONFIRMATION
so nothing gets silently rewritten. Run this, take it to A, get a yes or no
on each line.

Standard library only.
"""

from __future__ import annotations

import os

import data_adapter

DEFAULT_HANDOFF = os.path.join(
    os.path.expanduser("~"), "Downloads",
    "components_final_handoff(2) (2).csv")


# ---------------------------------------------------------------------------
# The judgements
# ---------------------------------------------------------------------------
#
# component_id -> (verdict, absorbed_into, reasoning)
#
# EXCLUDE_DUPLICATE  same hardware listed twice under different wording
# EXCLUDE_PARENT     a category heading whose children are priced separately
# EXCLUDE_ATTRIBUTE  a property of hardware already priced, not a purchase
# KEEP               genuinely distinct hardware

JUDGEMENTS = {
    "C27": (
        "EXCLUDE_DUPLICATE", "C15",
        "C15 is '0.33 NA EUV' and C27 is 'Standard 0.33 NA projection "
        "optics'. Same subsystem, same NA, same $25-50M range. One machine "
        "has one projection optics box.",
    ),
    "C43": (
        "EXCLUDE_DUPLICATE", "C04",
        "'Dual-pulse CO2 architecture' describes how C04's CO2 laser is "
        "operated. It is the architecture of a laser already priced, not a "
        "second laser. Identical $15-35M range is the tell.",
    ),
    "C01": (
        "EXCLUDE_PARENT", "C04+C05+C09+C11+C12",
        "'EUV light source' is the whole source subsystem. Its parts -- "
        "drive laser, amplifier, droplet generator, plasma, pulse sequence "
        "-- are each priced separately below. Counting the parent as well "
        "charges the source twice.",
    ),
    "C37": (
        "EXCLUDE_ATTRIBUTE", "C13+C14+C15",
        "'Multilayer Bragg mirror coating' is how the collector, "
        "illuminator and projection mirrors are made. Nobody buys the "
        "coating separately from the mirror it is on.",
    ),
    "C38": (
        "EXCLUDE_ATTRIBUTE", "C13+C14+C15",
        "'Ultra-smooth EUV mirror' is a surface specification of mirrors "
        "already priced, not an additional mirror.",
    ),
    # Deliberately kept -- these look like attributes but are separate hardware.
    "C39": ("KEEP", None,
            "Actuators are physical hardware bolted to the optics, procured "
            "and installed separately. Keep."),
    "C40": ("KEEP", None,
            "Thermal-control hardware (sensors, conditioning) is real "
            "equipment, not a property of a mirror. Keep."),
    "C05": ("KEEP", None,
            "A CO2 drive laser is a seed plus a multi-stage amplifier chain. "
            "The amplifier is genuinely separate hardware from the "
            "oscillator. Keep."),
    "C11": ("KEEP", None,
            "Priced as the source vessel and plasma-generation hardware "
            "rather than the plasma itself. Thin, but not obviously double "
            "counted. Flag to A."),
    "C21": ("KEEP", None,
            "In-vessel debris mitigation. Overlaps C35 in function but is "
            "different hardware -- mitigation stops tin travelling, capture "
            "removes what lands. Flag to A."),
    "C35": ("KEEP", None,
            "Tin capture and removal. See C21."),
}


# Categories whose only rows are Alternatives, with no Baseline to compare
# against. Each is an alternative to hardware that IS in the baseline, filed
# under a different `component` name.
ORPHAN_PARENTS = {
    "Tin target": ("C09", "Tin droplet generator",
                   "A preshaped microdroplet is an alternative target for "
                   "the same droplet generator."),
    "Illumination system": ("C14", "Illumination optics",
                            "The High-NA illuminator replaces the "
                            "conventional illumination optics."),
    "Debris mitigation": ("C21", "Particle control",
                          "Magnetic-field mitigation is an alternative "
                          "method to the baseline tin debris mitigation."),
    "Tin droplet shaping": ("C12", "Laser pulse sequence",
                            "Flattening the droplet before the main pulse "
                            "is a change to the pulse sequence."),
}


def reconcile(loaded: dict) -> dict:
    """Apply the judgements and report the corrected total."""
    components = {c["component_id"]: c for c in loaded["components"]}
    baseline = [c for c in loaded["components"] if c["is_baseline"]]

    kept, excluded = [], []
    for component in baseline:
        verdict, absorbed, reason = JUDGEMENTS.get(
            component["component_id"], ("KEEP", None, "not reviewed"))

        if verdict.startswith("EXCLUDE"):
            excluded.append({
                "component_id": component["component_id"],
                "name": component["name"],
                "category": component["category"],
                "cost_low_usd": component["cost_low_usd"],
                "cost_high_usd": component["cost_high_usd"],
                "cost_mid_usd": component["cost_usd"],
                "verdict": verdict,
                "absorbed_into": absorbed,
                "reasoning": reason,
                "status": "NEEDS_A_CONFIRMATION",
            })
        else:
            kept.append(component)

    def total(rows, key):
        return sum(r[key] if isinstance(r, dict) else 0 for r in rows)

    before_mid = sum(c["cost_usd"] for c in baseline)
    after_low = sum(c["cost_low_usd"] for c in kept)
    after_high = sum(c["cost_high_usd"] for c in kept)
    after_mid = sum(c["cost_usd"] for c in kept)

    benchmark = next(
        (b["cost_low_usd"] for b in loaded["benchmarks"]
         if "conventional" in b["name"].lower() and b["cost_low_usd"]), None)

    result = {
        "baseline_rows_before": len(baseline),
        "baseline_rows_after": len(kept),
        "excluded_count": len(excluded),
        "total_before_usd": before_mid,
        "total_after_low_usd": after_low,
        "total_after_high_usd": after_high,
        "total_after_mid_usd": after_mid,
        "removed_usd": before_mid - after_mid,
        "excluded": excluded,
        "kept": [{"component_id": c["component_id"], "name": c["name"],
                  "cost_mid_usd": c["cost_usd"]} for c in kept],
    }

    if benchmark:
        result["benchmark_usd"] = benchmark
        result["ratio_before"] = round(before_mid / benchmark, 3)
        result["ratio_after"] = round(after_mid / benchmark, 3)
        result["gap_after_pct"] = round(
            (after_mid - benchmark) / benchmark * 100, 1)
        result["benchmark_inside_range"] = (
            after_low <= benchmark <= after_high)

        result["verdict"] = (
            f"Excluding {len(excluded)} double-counted rows brings the bill "
            f"of materials from ${before_mid:,.0f} ({result['ratio_before']}x "
            f"the benchmark) to ${after_mid:,.0f} "
            f"({result['ratio_after']}x). Residual gap "
            f"{result['gap_after_pct']:+.1f}%, and the ${benchmark:,.0f} "
            f"benchmark "
            + ("falls inside" if result["benchmark_inside_range"]
               else "falls OUTSIDE")
            + f" the reconciled range ${after_low:,.0f}-${after_high:,.0f}."
        )

    return result


def orphan_report(loaded: dict) -> list:
    """Categories with alternatives but no baseline, and the proposed parent."""
    by_category: dict = {}
    for component in loaded["components"]:
        by_category.setdefault(component["category"], []).append(component)

    report = []
    for category, parts in sorted(by_category.items()):
        if any(p["is_baseline"] for p in parts):
            continue

        parent_id, parent_name, reason = ORPHAN_PARENTS.get(
            category, (None, None, "no parent identified"))

        report.append({
            "category": category,
            "alternatives": [
                {"component_id": p["component_id"], "name": p["name"],
                 "cost_mid_usd": p["cost_usd"]} for p in parts],
            "proposed_parent_id": parent_id,
            "proposed_parent": parent_name,
            "reasoning": reason,
            "status": "NEEDS_A_CONFIRMATION",
            "effect": (
                f"Re-filing these under '{parent_name}' gives them a baseline "
                f"to be compared against, so the optimizer can actually "
                f"consider them."
                if parent_name else
                "Without a parent these alternatives can never be selected."
            ),
        })

    return report


def main() -> int:
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HANDOFF
    if not os.path.exists(path):
        print(f"not found: {path}")
        return 1

    loaded = data_adapter.load_handoff(path)
    result = reconcile(loaded)
    orphans = orphan_report(loaded)

    print("=" * 74)
    print("  BILL OF MATERIALS RECONCILIATION")
    print("=" * 74)
    print(f"\n  Before : ${result['total_before_usd']:>13,.0f}   "
          f"({result['baseline_rows_before']} rows)")
    print(f"  After  : ${result['total_after_mid_usd']:>13,.0f}   "
          f"({result['baseline_rows_after']} rows)")
    print(f"  Removed: ${result['removed_usd']:>13,.0f}")
    if "benchmark_usd" in result:
        print(f"  A's own benchmark: ${result['benchmark_usd']:,.0f}")

    print(f"\n  EXCLUDED -- each needs A's yes or no\n")
    for row in result["excluded"]:
        print(f"    {row['component_id']}  {row['name'][:42]:<42} "
              f"-${row['cost_mid_usd']:>11,.0f}")
        print(f"          {row['verdict']}, absorbed into "
              f"{row['absorbed_into']}")
        print(f"          {row['reasoning']}")
        print()

    if "verdict" in result:
        print("  " + "-" * 70)
        print(f"\n  {result['verdict']}\n")

    print("  " + "-" * 70)
    print(f"\n  ORPHANED CATEGORIES -- alternatives with no baseline\n")
    for orphan in orphans:
        print(f"    {orphan['category']}")
        for alt in orphan["alternatives"]:
            print(f"      {alt['component_id']}  {alt['name'][:44]}")
        print(f"      -> file under {orphan['proposed_parent_id']} "
              f"({orphan['proposed_parent']})")
        print(f"      {orphan['reasoning']}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
