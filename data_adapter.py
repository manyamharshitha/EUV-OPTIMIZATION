"""
data_adapter.py  --  bridges Person A's handoff schema to the optimizer

Person A delivered `components_final_handoff.csv` in their own schema. It is
good, honest work -- costs given as ranges with a stated basis, everything
marked Modeled, `[NOT PUBLICLY DISCLOSED]` where ASML publishes nothing. But
it does not match what `optimizer.py` reads, and three columns the optimizer
scores on are largely or entirely absent.

This module converts the schema and reports exactly what is missing rather
than filling gaps with invented numbers.

WHAT A SUPPLIED, AND WHAT IT MEANS FOR SCORING
----------------------------------------------

    cost          COMPLETE.  Every row has a low/high range and a stated
                  basis. We use the midpoint and keep the range.

    efficiency    6 rows out of 45.  Only the laser-source options carry a
                  measured conversion efficiency. Everything else is blank,
                  correctly, because no public figure exists.

    lead time     ABSENT.  There is no procurement-lead-time column at all.

The optimizer's third axis was timeline. Rather than invent lead times, this
adapter substitutes A's `technology_readiness` column, which is real data:
industrial production hardware is low-risk, research-stage hardware is high-
risk. That is a defensible proxy for "how long until you could actually have
one", and it comes from A's file rather than from us.

The readiness-to-number mapping IS a modelling choice. It is declared in
READINESS_RISK below so a judge can see it and argue with it.
"""

from __future__ import annotations

import csv
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# A's technology_readiness values -> a 0..1 risk score, where 1.0 means
# "buy it today" and low values mean "this is a laboratory result".
# MODELLED MAPPING. A supplied the categories; the numbers are ours.
READINESS_RISK = {
    "industrial/production": 1.00,
    "commercial benchmark": 1.00,
    "research-stage": 0.40,
    "model assumption": 0.50,
    "": 0.50,
}

# Vendor -> country. Derived from A's `source` column, which names real
# organisations. This is public fact, not estimation.
VENDOR_COUNTRY = {
    "ASML": "Netherlands",
    "ZEISS": "Germany",
    "TRUMPF": "Germany",
    "VU Amsterdam": "Netherlands",
    "Gigaphoton": "Japan",
}

# Rows that are not purchasable hardware and must not enter the optimiser.
NON_COMPONENT_TYPES = {"benchmark"}


def parse_money(raw: str) -> float | None:
    """
    '$10M' -> 10000000.0,  '$500K' -> 500000.0,  '$0' -> 0.0

    Returns None for anything unparseable, including
    '[NOT PUBLICLY DISCLOSED]'.
    """
    if raw is None:
        return None
    text = str(raw).strip().replace("$", "").replace(",", "")
    if not text or text.startswith("["):
        return None

    match = re.match(r"^([\d.]+)\s*([MKB]?)$", text, re.IGNORECASE)
    if not match:
        try:
            return float(text)
        except ValueError:
            return None

    value = float(match.group(1))
    multiplier = {"": 1, "K": 1e3, "M": 1e6, "B": 1e9}[match.group(2).upper()]
    return value * multiplier


def parse_percent(raw: str) -> float | None:
    """'5.0' -> 0.05.  Blank or bracketed placeholder -> None."""
    if raw is None:
        return None
    text = str(raw).strip().replace("%", "")
    if not text or text.startswith("["):
        return None
    try:
        return float(text) / 100.0
    except ValueError:
        return None


def country_for(source: str) -> str:
    """Map A's source string to a country, or UNKNOWN."""
    if not source:
        return "UNKNOWN"
    for vendor, country in VENDOR_COUNTRY.items():
        if vendor.lower() in source.lower():
            return country
    return "UNKNOWN"


def load_handoff(path: str) -> dict:
    """
    Read A's file and return converted components plus a full account of what
    could not be converted and why.
    """
    with open(path, newline="", encoding="utf-8-sig") as handle:
        raw_rows = [r for r in csv.DictReader(handle) if r.get("component_id")]

    components = []
    benchmarks = []
    issues = []

    for row in raw_rows:
        cid = row["component_id"].strip()
        option_type = row.get("option_type", "").strip()
        component = row.get("component", "").strip()

        low = parse_money(row.get("cost_low_usd"))
        high = parse_money(row.get("cost_high_usd"))

        # Benchmarks and zero-cost characteristics are not selectable parts.
        if option_type.lower() in NON_COMPONENT_TYPES:
            benchmarks.append({
                "id": cid,
                "name": row.get("option", "").strip(),
                "metric": row.get("performance_metric", "").strip(),
                "value": row.get("performance_value", "").strip(),
                "cost_low_usd": low,
                "cost_high_usd": high,
                "source": row.get("source", "").strip(),
                "notes": row.get("notes", "").strip(),
            })
            continue

        if low is None or high is None:
            issues.append({
                "component_id": cid, "severity": "excluded",
                "problem": "cost could not be parsed",
                "detail": f"low={row.get('cost_low_usd')!r} "
                          f"high={row.get('cost_high_usd')!r}",
            })
            continue

        if low == 0 and high == 0:
            issues.append({
                "component_id": cid, "severity": "excluded",
                "problem": "zero cost -- characteristic, not purchasable hardware",
                "detail": row.get("cost_basis", ""),
            })
            continue

        efficiency = parse_percent(row.get("efficiency_pct"))
        readiness = row.get("technology_readiness", "").strip().lower()
        risk = READINESS_RISK.get(readiness)

        if risk is None:
            issues.append({
                "component_id": cid, "severity": "warning",
                "problem": f"unrecognised technology_readiness {readiness!r}",
                "detail": "defaulted risk to 0.5",
            })
            risk = 0.5

        if efficiency is None:
            issues.append({
                "component_id": cid, "severity": "info",
                "problem": "no efficiency figure",
                "detail": "excluded from efficiency scoring",
            })

        components.append({
            "component_id": cid,
            "category": component,
            "subsystem": row.get("subsystem", "").strip(),
            "name": row.get("option", "").strip(),
            "supplier": row.get("source", "").strip(),
            "country": country_for(row.get("source", "")),
            "cost_low_usd": low,
            "cost_high_usd": high,
            "cost_usd": (low + high) / 2.0,
            "cost_uncertainty_pct": round((high - low) / ((low + high) / 2.0) * 100, 1)
            if (low + high) else 0.0,
            "efficiency": efficiency,
            "has_efficiency": efficiency is not None,
            "readiness": row.get("technology_readiness", "").strip(),
            "readiness_risk": risk,
            "availability": row.get("availability", "").strip(),
            "is_baseline": option_type.lower() == "baseline",
            "performance_metric": row.get("performance_metric", "").strip(),
            "performance_value": row.get("performance_value", "").strip(),
            "unit": row.get("unit", "").strip(),
            "data_type": row.get("data_type", "").strip(),
            "cost_type": row.get("cost_type", "").strip(),
            "source": row.get("source", "").strip(),
            "notes": row.get("notes", "").strip(),
        })

    return {
        "components": components,
        "benchmarks": benchmarks,
        "issues": issues,
        "source_file": path,
        "rows_read": len(raw_rows),
    }


def analyse(loaded: dict) -> dict:
    """What can actually be optimised, and what cannot."""
    components = loaded["components"]

    by_category: dict = {}
    for component in components:
        by_category.setdefault(component["category"], []).append(component)

    choosable = {k: v for k, v in by_category.items() if len(v) > 1}
    fixed = {k: v for k, v in by_category.items() if len(v) == 1}

    multi_baseline = {
        k: [c["component_id"] for c in v if c["is_baseline"]]
        for k, v in by_category.items()
        if sum(1 for c in v if c["is_baseline"]) > 1
    }
    no_baseline = [k for k, v in by_category.items()
                   if not any(c["is_baseline"] for c in v)]

    combinations = 1
    for options in choosable.values():
        combinations *= len(options)

    with_efficiency = [c for c in components if c["has_efficiency"]]

    return {
        "total_components": len(components),
        "categories": len(by_category),
        "choosable_categories": len(choosable),
        "fixed_categories": len(fixed),
        "combinations": combinations,
        "choosable": {k: len(v) for k, v in sorted(choosable.items())},
        "fixed": sorted(fixed),
        "multi_baseline": multi_baseline,
        "no_baseline": no_baseline,
        "efficiency_coverage": {
            "present": len(with_efficiency),
            "total": len(components),
            "pct": round(len(with_efficiency) / len(components) * 100, 1)
            if components else 0.0,
            "components": [c["component_id"] for c in with_efficiency],
        },
        "cost_coverage": {"present": len(components), "total": len(components),
                          "pct": 100.0},
        "lead_time_coverage": {"present": 0, "total": len(components),
                               "pct": 0.0,
                               "note": "A's schema has no lead-time column. "
                                       "technology_readiness is used as a risk "
                                       "proxy instead."},
    }


def to_optimizer_csv(loaded: dict, output_path: str) -> dict:
    """
    Write a CSV in the schema `optimizer.py` reads.

    Efficiency is the difficult column. Where A supplied no figure we write
    the row with an empty efficiency rather than a fabricated one, and the
    optimizer treats those categories as cost-and-risk decisions only.
    """
    import json

    components = loaded["components"]
    written = 0

    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "component_id", "category", "name", "supplier", "country",
            "cost_usd", "cost_low_usd", "cost_high_usd", "efficiency",
            "readiness_risk", "readiness", "lead_time_years", "is_baseline",
            "specs_json", "source", "confidence", "notes",
        ])

        for c in components:
            writer.writerow([
                c["component_id"],
                c["category"],
                c["name"],
                c["supplier"] or "UNSPECIFIED",
                c["country"],
                f"{c['cost_usd']:.0f}",
                f"{c['cost_low_usd']:.0f}",
                f"{c['cost_high_usd']:.0f}",
                f"{c['efficiency']:.4f}" if c["has_efficiency"] else "",
                f"{c['readiness_risk']:.2f}",
                c["readiness"],
                "",                       # lead_time: A supplied none
                "1" if c["is_baseline"] else "0",
                json.dumps({}),
                c["source"] or "MODELED",
                "MODELED" if c["cost_type"].lower() == "modeled" else "MEDIUM",
                c["notes"],
            ])
            written += 1

    return {"written": written, "path": output_path}


if __name__ == "__main__":
    import sys

    default = os.path.join(
        os.path.expanduser("~"), "Downloads",
        "components_final_handoff(2) (2).csv")
    path = sys.argv[1] if len(sys.argv) > 1 else default

    if not os.path.exists(path):
        print(f"not found: {path}")
        raise SystemExit(1)

    loaded = load_handoff(path)
    report = analyse(loaded)

    print("=" * 70)
    print("  PERSON A HANDOFF -- CONVERSION REPORT")
    print("=" * 70)
    print(f"  rows read            : {loaded['rows_read']}")
    print(f"  usable components    : {report['total_components']}")
    print(f"  benchmarks set aside : {len(loaded['benchmarks'])}")
    print(f"  rows excluded        : "
          f"{sum(1 for i in loaded['issues'] if i['severity'] == 'excluded')}")

    print(f"\n  COVERAGE OF THE THREE SCORING AXES")
    print(f"    cost       {report['cost_coverage']['pct']:>5.1f}%  "
          f"({report['cost_coverage']['present']}/"
          f"{report['cost_coverage']['total']})")
    print(f"    efficiency {report['efficiency_coverage']['pct']:>5.1f}%  "
          f"({report['efficiency_coverage']['present']}/"
          f"{report['efficiency_coverage']['total']})  "
          f"{report['efficiency_coverage']['components']}")
    print(f"    lead time  {report['lead_time_coverage']['pct']:>5.1f}%  "
          f"-- column absent; using technology_readiness as risk proxy")

    print(f"\n  OPTIMISABLE STRUCTURE")
    print(f"    categories with a real choice : "
          f"{report['choosable_categories']}")
    print(f"    categories with one option    : {report['fixed_categories']}")
    print(f"    total combinations            : {report['combinations']:,}")
    for category, count in report["choosable"].items():
        print(f"      {category:<26} {count} options")

    if report["multi_baseline"]:
        print(f"\n  AMBIGUITY -- more than one row marked Baseline:")
        for category, ids in report["multi_baseline"].items():
            print(f"    {category:<26} {ids}")

    if report["no_baseline"]:
        print(f"\n  AMBIGUITY -- no Baseline row:")
        for category in report["no_baseline"]:
            print(f"    {category}")

    excluded = [i for i in loaded["issues"] if i["severity"] == "excluded"]
    if excluded:
        print(f"\n  EXCLUDED ROWS")
        for issue in excluded:
            print(f"    {issue['component_id']}: {issue['problem']}")

    output = os.path.join(BASE_DIR, "data", "components_from_A.csv")
    result = to_optimizer_csv(loaded, output)
    print(f"\n  wrote {result['written']} rows -> {result['path']}")
