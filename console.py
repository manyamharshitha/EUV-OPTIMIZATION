"""
console.py  --  interactive test console

Everything the backend can do, from one menu. No arguments to remember.

    python console.py
"""

from __future__ import annotations

import backend


def ask(prompt: str, default=None, cast=float):
    """Read one value. Blank keeps the default. Blank with no default = None."""
    suffix = f" [{default}]" if default is not None else " [any]"
    raw = input(f"  {prompt}{suffix}: ").strip()
    if not raw:
        return default
    try:
        return cast(raw)
    except ValueError:
        print("    not valid, using default")
        return default


def pick(prompt: str, options: list, default: int = 0) -> str:
    print(f"\n  {prompt}")
    for i, option in enumerate(options, 1):
        print(f"    {i}. {option}")
    raw = input(f"  choice [{default + 1}]: ").strip()
    try:
        index = int(raw) - 1 if raw else default
        return options[index] if 0 <= index < len(options) else options[default]
    except ValueError:
        return options[default]


def money(value) -> str:
    return f"${value:,.0f}" if value is not None else "-"


def as_efficiency(value):
    """
    Accept 0.55 or 55 or 55% and mean the same thing.

    Everyone thinks in percent. Silently treating 55 as "efficiency >= 5500%"
    produced zero feasible configurations with no explanation, which looked
    like the optimizer was broken.
    """
    if value is None:
        return None
    if value > 1.0:
        converted = value / 100.0
        print(f"    (read {value:g} as {converted:.2%})")
        return converted
    return value


def as_dollars(value):
    """Accept 150 (millions) or 150000000 (dollars)."""
    if value is None:
        return None
    dollars = value if value > 10_000 else value * 1e6
    if value > 10_000:
        print(f"    (read {value:,.0f} as {money(dollars)})")
    return dollars


def ask_number(prompt: str, default=None):
    """Number entry that tolerates $, commas and % in pasted values."""
    suffix = f" [{default}]" if default is not None else " [any]"
    raw = input(f"  {prompt}{suffix}: ").strip()
    if not raw:
        return default
    cleaned = raw.replace("$", "").replace(",", "").replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        print(f"    '{raw}' is not a number, using {default}")
        return default


def diagnose(budget_usd, min_efficiency, max_timeline_years):
    """
    Nothing was feasible. Say which constraint is responsible instead of
    leaving the user to guess.
    """
    ranges = backend.achievable_ranges()
    blocking = []

    if budget_usd is not None and budget_usd < ranges["cost_usd"]["min"]:
        blocking.append(
            f"budget {money(budget_usd)} is below the cheapest possible "
            f"machine at {money(ranges['cost_usd']['min'])}")

    if min_efficiency is not None:
        best = ranges["efficiency_pct"]["max"] / 100.0
        if min_efficiency > best:
            blocking.append(
                f"minimum efficiency {min_efficiency:.2%} exceeds the best "
                f"achievable {best:.2%}")

    if max_timeline_years is not None:
        fastest = ranges["timeline_years"]["min"]
        if max_timeline_years < fastest:
            blocking.append(
                f"timeline {max_timeline_years} yr is shorter than the "
                f"fastest possible build at {fastest} yr")

    if blocking:
        print("\n  Why nothing is feasible:")
        for reason in blocking:
            print(f"    - {reason}")
        return

    # Each limit is individually reachable, so it is the combination that
    # fails. Isolate each one properly -- the other two must be relaxed all
    # the way, or run()'s defaults quietly re-apply themselves and every row
    # reads zero.
    OPEN = {"budget_usd": 1e15, "min_efficiency": 0.0,
            "max_timeline_years": 1e6}

    print("\n  Each limit is reachable on its own. It is the combination "
          "that fails:")
    for label, key, value in (
            ("budget alone", "budget_usd", budget_usd),
            ("efficiency alone", "min_efficiency", min_efficiency),
            ("timeline alone", "max_timeline_years", max_timeline_years)):
        if value is None:
            continue
        kwargs = dict(OPEN)
        kwargs[key] = value
        count = backend.run(**kwargs)["results"]["feasible_count"]
        print(f"    {label:<18} {count:>6,} feasible on its own")

    if budget_usd is not None and max_timeline_years is not None:
        outcome = backend.solve_for("efficiency", max_cost=budget_usd,
                                    max_timeline=max_timeline_years)
        if outcome.get("achievable") is not None:
            print(f"\n  Best efficiency reachable inside {money(budget_usd)} "
                  f"and {max_timeline_years} yr: {outcome['achievable']:.2%}")
            print(f"  Set the efficiency requirement to that or lower.")
        else:
            cheapest = backend.solve_for("cost",
                                         max_timeline=max_timeline_years)
            if cheapest.get("achievable") is not None:
                print(f"\n  No machine at all fits {money(budget_usd)} within "
                      f"{max_timeline_years} yr.")
                print(f"  The cheapest buildable in {max_timeline_years} yr "
                      f"is {money(cheapest['achievable'])} -- raise the budget "
                      f"to that, or allow more time.")


# ---------------------------------------------------------------------------

def do_optimize():
    print("\n--- OPTIMIZE (forward: constraints in, machines out) ---")
    budget = as_dollars(ask_number("budget in $M", 180.0))
    efficiency = as_efficiency(ask_number("min efficiency (0.5 or 50%)", 0.50))
    timeline = ask_number("max timeline years", 8.0)

    print(f"\n  running: budget {money(budget)}, "
          f"efficiency >= {efficiency:.2%}, timeline <= {timeline} yr")

    result = backend.run(budget_usd=budget,
                         min_efficiency=efficiency,
                         max_timeline_years=timeline)

    res = result["results"]
    print(f"\n  evaluated {res['combinations_evaluated']:,}, "
          f"{res['feasible_count']:,} feasible")

    if not res["top_configurations"]:
        diagnose(budget, efficiency, timeline)
        return

    print(f"  baseline {money(res['baseline']['total_cost_usd'])}  ->  "
          f"saving {res['savings']['percent']}%\n")
    for c in res["top_configurations"]:
        print(f"    {c['rank']}. {money(c['total_cost_usd']):>14}   "
              f"eff {c['efficiency_pct']:>5}%   {c['timeline_years']:>4} yr")

    sim = result["simulation"]
    print(f"\n  resolution {sim['resolution_nm']} nm   "
          f"throughput {sim['throughput_wph']} wph   "
          f"7nm met: {sim['resolution_target_met']}")
    print(f"  particle risk: {result['particles']['risk_level']}")


def do_solve():
    print("\n--- INVERSE SOLVE (pin what you know, solve the rest) ---")
    unknown = pick("solve for which?", ["efficiency", "cost", "timeline"])

    print(f"\n  Now give me what you DO know (blank = unconstrained)")
    cost = eff = time_limit = None
    if unknown != "cost":
        cost = as_dollars(ask_number("max cost in $M", None))
    if unknown != "efficiency":
        eff = as_efficiency(ask_number("min efficiency (0.5 or 50%)", None))
    if unknown != "timeline":
        time_limit = ask_number("max timeline years", None)

    outcome = backend.solve_for(unknown, max_cost=cost, min_efficiency=eff,
                                max_timeline=time_limit)
    print(f"\n  {outcome['explanation']}")

    config = outcome.get("configuration")
    if config:
        print(f"\n  that machine: {money(config['total_cost_usd'])}, "
              f"{config['efficiency_pct']}% efficiency, "
              f"{config['timeline_years']} years")
        for c in config["components"]:
            flag = "  [HYPOTHETICAL]" if c["is_hypothetical"] else ""
            print(f"    {c['category']:<20} {c['name'][:38]:<38} "
                  f"{money(c['cost_usd']):>13}{flag}")


def do_cost_cut():
    print("\n--- COST REDUCTION (how do I get to a target?) ---")
    target = as_dollars(ask_number("target cost in $M", 130.0))
    real_only = input("  real suppliers only? [y/N]: ").strip().lower() == "y"

    advice = backend.cost_reduction(target_cost_usd=target,
                                    exclude_hypothetical=real_only)
    plan = advice["pathway"]

    if plan.get("already_met"):
        print(f"\n  {plan['explanation']}")
        return

    print()
    for step in plan["steps"]:
        flag = "  [HYPOTHETICAL]" if step["is_hypothetical"] else ""
        print(f"    {step['step']}. {step['category']}")
        print(f"       {step['replace'][:44]}")
        print(f"       -> {step['with'][:44]}{flag}")
        print(f"       saves {money(step['cost_saved_usd'])}, "
              f"costs {step['efficiency_lost_pct']:.2f} eff pts   "
              f"=> {money(step['running_cost_usd'])} @ "
              f"{step['running_efficiency_pct']}%")
    print(f"\n  {plan['explanation']}")

    print("\n  best-value swaps available (least lost per $M saved):")
    for option in advice["best_value_swaps"]:
        flag = " [HYP]" if option["is_hypothetical"] else ""
        print(f"    {option['category']:<20} saves "
              f"{money(option['cost_saved_usd']):>13}  "
              f"costs {option['efficiency_lost_pct']:>5.2f} pts{flag}")


def do_design():
    print("\n--- DESIGN OPTIMIZATION (tell me what you want) ---")
    goals = list(backend.design_goals()["goals"].items())
    labels = [f"{k:<16} {v}" for k, v in goals]
    chosen = pick("what matters most?", labels, default=6)
    goal = chosen.split()[0]

    print("\n  constraints (blank = none)")
    budget = as_dollars(ask_number("budget in $M", None))
    eff = as_efficiency(ask_number("min efficiency (0.5 or 50%)", None))
    wph = ask_number("min throughput wafers/hr", None)
    real_only = input("  real suppliers only? [y/N]: ").strip().lower() == "y"

    outcome = backend.optimize_design(
        goal=goal,
        budget_usd=budget,
        min_efficiency=eff,
        min_throughput_wph=wph,
        exclude_hypothetical=real_only)

    if not outcome["ok"]:
        print(f"\n  INFEASIBLE: {outcome['reason']}")
        if outcome.get("suggestion"):
            print(f"  {outcome['suggestion']}")
        return

    print(f"\n  {outcome['explanation']}\n")
    for c in outcome["best"]["components"]:
        flag = "  [HYPOTHETICAL]" if c["is_hypothetical"] else ""
        print(f"    {c['category']:<20} {c['name'][:36]:<36} "
              f"{money(c['cost_usd']):>13}{flag}")


def do_compare_goals():
    print("\n--- ALL GOALS SIDE BY SIDE ---\n")
    comparison = backend.compare_design_goals()["comparison"]
    print(f"    {'goal':<16} {'cost':>14} {'eff':>7} {'res':>8} "
          f"{'wph':>7} {'yrs':>5} {'dom':>6}")
    print("    " + "-" * 68)
    for goal, row in comparison.items():
        if row.get("infeasible"):
            print(f"    {goal:<16} infeasible")
            continue
        print(f"    {goal:<16} {money(row['cost_usd']):>14} "
              f"{row['efficiency_pct']:>6.1f}% {row['resolution_nm']:>7.1f} "
              f"{row['throughput_wph']:>7.0f} {row['timeline_years']:>5.1f} "
              f"{row['domestic_content_pct']:>5.0f}%")
    print("\n  No row is 'the' answer. They are different trade-offs.")


def do_alternatives():
    print("\n--- ALTERNATIVES FOR ONE CATEGORY ---")
    categories = backend.run()["results"]["categories"]
    category = pick("which category?", categories)

    data = backend.alternatives_for(category)
    print(f"\n  {data['option_count']} options "
          f"({data['hypothetical_count']} hypothetical)\n")
    print(f"    {'name':<38} {'cost':>13} {'eff':>7} {'yrs':>5}  supplier")
    print("    " + "-" * 76)
    for row in data["options"]:
        marker = " *" if row["is_baseline"] else "  "
        flag = " [HYP]" if row["is_hypothetical"] else ""
        print(f"  {marker}{row['name'][:37]:<38} {money(row['cost_usd']):>13} "
              f"{row['efficiency_pct']:>6}% {row['lead_time_years']:>5} "
              f" {row['supplier']}{flag}")
    print("\n    * = baseline")


def do_ranges():
    print("\n--- WHAT IS POSSIBLE AT ALL ---\n")
    ranges = backend.achievable_ranges()
    print(f"    cost       {money(ranges['cost_usd']['min'])} .. "
          f"{money(ranges['cost_usd']['max'])}")
    print(f"    efficiency {ranges['efficiency_pct']['min']}% .. "
          f"{ranges['efficiency_pct']['max']}%")
    print(f"    timeline   {ranges['timeline_years']['min']} .. "
          f"{ranges['timeline_years']['max']} years")
    print(f"\n    {ranges['note']}")

    frontier = backend.tradeoff_frontier(max_points=12)
    print(f"\n  {frontier['explanation']}\n")
    print(f"    {'cost':>14} {'eff':>8} {'yrs':>6}")
    for point in frontier["points"]:
        print(f"    {money(point['cost_usd']):>14} "
              f"{point['efficiency_pct']:>7}% {point['timeline_years']:>6}")


def do_screen():
    import inspect_backend
    number = ask("which screen 1-9?", 9, int)
    if number not in inspect_backend.SCREENS:
        print("  1 to 9 only")
        return
    inspect_backend.SCREENS[number](backend.run())


def do_proof():
    import subprocess
    import sys
    subprocess.run([sys.executable, "demo_proof.py"])


ACTIONS = [
    ("Optimize (budget/efficiency/time in, machines out)", do_optimize),
    ("Inverse solve (pin two, solve the third)", do_solve),
    ("Cost reduction (how do I hit a target?)", do_cost_cut),
    ("Design optimization (tell it what you want)", do_design),
    ("Compare all 7 goals", do_compare_goals),
    ("Alternatives for one category", do_alternatives),
    ("What is possible at all + trade-off frontier", do_ranges),
    ("View a screen (1-9)", do_screen),
    ("Run the 38-claim proof suite", do_proof),
]


def main():
    print("=" * 70)
    print("  EUV OPTIMIZER -- BACKEND TEST CONSOLE")
    print("=" * 70)

    while True:
        print()
        for i, (label, _) in enumerate(ACTIONS, 1):
            print(f"  {i}. {label}")
        print("  0. quit")

        raw = input("\n  > ").strip()
        if raw in ("0", "q", "quit", "exit"):
            break

        try:
            index = int(raw) - 1
        except ValueError:
            print("  enter a number")
            continue

        if not 0 <= index < len(ACTIONS):
            print("  out of range")
            continue

        try:
            ACTIONS[index][1]()
        except (KeyboardInterrupt, EOFError):
            print("\n  cancelled")
        except Exception as exc:
            print(f"\n  ERROR: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nbye")
