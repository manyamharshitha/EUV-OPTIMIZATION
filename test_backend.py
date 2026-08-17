"""
test_backend.py  --  interactive backend tester

Play judge. Change the constraints, watch the backend respond.

    python test_backend.py            interactive
    python test_backend.py --sweep    automated sweep, no input needed
"""

from __future__ import annotations

import sys
import time

import backend


def show(result: dict, label: str = "") -> None:
    if label:
        print(f"\n--- {label} ---")

    if not result["ok"]:
        print(f"  FAILED: {result['errors']}")
        return

    res = result["results"]
    sim = result["simulation"]
    top = res["top_configurations"]

    print(f"  combinations evaluated : {res['combinations_evaluated']:,}")
    print(f"  feasible               : {res['feasible_count']:,}")

    if not top:
        print("  no configuration satisfies these constraints")
        return

    best = top[0]
    base = res["baseline"]["total_cost_usd"]

    print(f"  baseline cost          : ${base:,.0f}")
    print(f"  best cost              : ${best['total_cost_usd']:,.0f}")
    print(f"  saving                 : {res['savings']['percent']}%")
    print(f"  efficiency             : {best['efficiency_pct']}%")
    print(f"  timeline               : {best['timeline_years']} years")
    print(f"  resolution             : {sim['resolution_nm']} nm "
          f"(7 nm met: {sim['resolution_target_met']})")
    print(f"  throughput             : {sim['throughput_wph']} wafers/hr")
    print(f"  particle risk          : {result['particles']['risk_level']}")
    print(f"  AI backend             : "
          f"{result['ai']['analysis']['backend'] if result['ai']['status'] == 'ok' else 'n/a'}")

    print("\n  top 5:")
    for config in top[:5]:
        print(f"    {config['rank']}. ${config['total_cost_usd']:>13,.0f}   "
              f"eff {config['efficiency_pct']:>5}%   "
              f"{config['timeline_years']:>4} yr   "
              f"score {config['score']:.4f}")


def sweep() -> None:
    """Automated: the cases a judge is most likely to try."""
    cases = [
        ("default", {}),
        ("tight budget $120M", {"budget_usd": 120e6}),
        ("very tight $80M", {"budget_usd": 80e6}),
        ("impossible $10M", {"budget_usd": 10e6}),
        ("high efficiency 85%", {"min_efficiency": 0.85}),
        ("impossible efficiency 99%", {"min_efficiency": 0.99}),
        ("fast timeline 4 yr", {"max_timeline_years": 4.0}),
        ("cost-focused", {"weight_cost": 0.9, "weight_efficiency": 0.05,
                          "weight_time": 0.05}),
        ("efficiency-focused", {"weight_cost": 0.05, "weight_efficiency": 0.9,
                                "weight_time": 0.05}),
    ]

    for label, kwargs in cases:
        start = time.time()
        result = backend.run(**kwargs)
        show(result, f"{label}  ({time.time() - start:.2f}s)")


def interactive() -> None:
    print("Interactive backend test. Enter to accept the default.\n")

    def ask(prompt: str, default: float) -> float:
        raw = input(f"  {prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            print("    not a number, using default")
            return default

    while True:
        budget = ask("budget in millions USD", 250.0)
        efficiency = ask("minimum efficiency 0-1", 0.30)
        timeline = ask("max timeline years", 10.0)

        start = time.time()
        result = backend.run(
            budget_usd=budget * 1e6,
            min_efficiency=efficiency,
            max_timeline_years=timeline,
        )
        show(result, f"result ({time.time() - start:.2f}s)")

        if input("\n  again? [y/N]: ").strip().lower() != "y":
            break


if __name__ == "__main__":
    if "--sweep" in sys.argv:
        sweep()
    else:
        try:
            interactive()
        except (KeyboardInterrupt, EOFError):
            print("\nstopped")
