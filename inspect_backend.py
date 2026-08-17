"""
inspect_backend.py  --  see every screen's backend data

`backend.py` prints a 13-line summary, which hides most of what it returns.
This prints all nine screens plus the interactive endpoints, so you can see
exactly what the frontend has to work with.

    python inspect_backend.py            all nine screens
    python inspect_backend.py 5          just screen 5
    python inspect_backend.py --api      the on-demand endpoints
"""

from __future__ import annotations

import sys

import backend


def rule(title: str) -> None:
    print("\n" + "=" * 74)
    print(f"  {title}")
    print("=" * 74)


def screen_1(r):
    rule("SCREEN 1 -- USER INPUT")
    ui = r["user_input"]
    print(f"  budget          : ${ui['budget_usd']:,.0f}")
    print(f"  min efficiency  : {ui['min_efficiency']}")
    print(f"  max timeline    : {ui['max_timeline_years']} years")
    print(f"  weights         : {ui['weights']}")
    print(f"  ISO class       : {ui['iso_class']}")
    print(f"  dose            : {ui['dose_mj_cm2']} mJ/cm2")
    print("\n  slider bounds (from interactivity/):")
    for name, bounds in r["interactivity"].items():
        if isinstance(bounds, dict) and "min" in bounds:
            print(f"    {name:<20} {bounds['min']} .. {bounds['max']} "
                  f"(step {bounds['step']})")


def screen_2(r):
    rule("SCREEN 2 -- DISPLAY RESULTS")
    res = r["results"]
    print(f"  combinations    : {res['combinations_evaluated']:,}")
    print(f"  feasible        : {res['feasible_count']:,}")
    print(f"  baseline cost   : ${res['baseline']['total_cost_usd']:,.0f}")
    print(f"  savings         : ${res['savings']['absolute_usd']:,.0f} "
          f"({res['savings']['percent']}%)")
    print("\n  top 5:")
    for c in res["top_configurations"]:
        print(f"    {c['rank']}. ${c['total_cost_usd']:>13,.0f}  "
              f"eff {c['efficiency_pct']:>5}%  {c['timeline_years']:>4} yr  "
              f"score {c['score']:.4f}")


def screen_3(r):
    rule("SCREEN 3 -- VISUALIZATION")
    for name, series in r["visualization"].items():
        print(f"  {name:<20} {len(series)} points")
        for item in series[:3]:
            label = item.get("label", item.get("category", "?"))
            value = item.get("value", item.get("cost_usd", ""))
            print(f"      {str(label)[:40]:<40} {value}")
        if len(series) > 3:
            print(f"      ... {len(series) - 3} more")


def screen_4(r):
    rule("SCREEN 4 -- INTERACTIVITY")
    inter = r["interactivity"]
    for name, bounds in inter.items():
        if isinstance(bounds, dict) and "min" in bounds:
            print(f"  {name:<22} {bounds['min']} .. {bounds['max']}")
    for name in ("categories", "countries", "suppliers"):
        if name in inter:
            print(f"  {name:<22} {inter[name]}")


def screen_5(r):
    rule("SCREEN 5 -- PARTICLE MANAGEMENT")
    p = r["particles"]
    print(f"  ISO class            : {p['iso_class']}")
    print(f"  killer particle size : {p['killer_particle_size_um']} um")
    print(f"  particles per m3     : {p['particles_per_m3']:,.0f}")
    print(f"  defect density       : {p['defect_density_per_cm2']} /cm2")
    print(f"  yield                : {p['yield_pct']}%")
    print(f"  yield loss           : {p['yield_loss_pct']}%")
    print(f"  RISK LEVEL           : {p['risk_level']}")
    print(f"  build cost           : ${p['build_cost_usd']:,.0f}")
    print(f"  annual operating     : ${p['annual_operating_cost_usd']:,.0f}")
    print(f"  cost of yield loss   : ${p['cost_of_yield_loss_usd']:,.0f}")
    print(f"  TOTAL                : ${p['total_cleanliness_cost_usd']:,.0f}")
    print(f"  recommended class    : ISO {p['recommended_iso_class']}")
    print(f"\n  {p['recommendation']}")


def screen_6(r):
    rule("SCREEN 6 -- CLEANLINESS")
    c = r["cleanliness"]
    print(f"  current ISO {c['current_class']}, recommended ISO "
          f"{c['recommended_class']}\n")
    print(f"    {'ISO':<5} {'yield':>8} {'risk':<10} {'operating':>15} "
          f"{'yield loss':>15} {'total':>15}")
    print("    " + "-" * 70)
    for row in c["comparison"]:
        marker = "  <-- current" if row["iso_class"] == c["current_class"] else ""
        print(f"    {row['iso_class']:<5} {row['yield_pct']:>7}% "
              f"{row['risk_level']:<10} "
              f"${row['annual_operating_cost_usd']:>14,.0f} "
              f"${row['cost_of_yield_loss_usd']:>14,.0f} "
              f"${row['total_cleanliness_cost_usd']:>14,.0f}{marker}")


def screen_7(r):
    rule("SCREEN 7 -- AI PRECISION & DESIGN")
    ai = r["ai"]
    print(f"  status  : {ai['status']}")
    if ai["status"] != "ok":
        print(f"  reason  : {ai.get('reason')}")
        return

    print(f"  backend : {ai['analysis']['backend']}  "
          f"(local_model = real AI, rule_based = deterministic templates)")

    print("\n  REASONING -- why the optimizer chose this:")
    for point in ai["reasoning"]["points"]:
        print(f"    * {point}")

    print("\n  PRECISION + DESIGN:")
    for point in ai["analysis"]["points"]:
        print(f"    * {point}")


def screen_8(r):
    rule("SCREEN 8 -- EXTERNAL DATA LEARNING")
    dl = r["data_learning"]
    print(f"  status   : {dl['status']}")
    print(f"  patterns : {len(dl['patterns'])}\n")
    for pattern in dl["patterns"]:
        print(f"    [{pattern['quality']:<8}] {pattern['model_form']:<12} "
              f"R2={pattern['r_squared']:.3f}  n={pattern['n_points']} "
              f"({pattern['n_published']} published)")
        print(f"      {pattern['x']} -> {pattern['y']}")
        for warning in pattern["warnings"]:
            print(f"      ! {warning}")

    prediction = dl["predictions"]
    if prediction.get("available"):
        print(f"\n  CE prediction at 30 kW: {prediction['predicted']} "
              f"[{prediction['low']}, {prediction['high']}] "
              f"confidence {prediction['confidence']}")


def screen_9(r):
    rule("SCREEN 9 -- EUV SIMULATION")
    s = r["simulation"]
    print("  Physics chain:\n")
    for stage in s["stages"]:
        print(f"    {stage['label']:<32} {stage['value']:>12} {stage['unit']}")

    print(f"\n  numerical aperture   : {s['numerical_aperture']}")
    print(f"  k1                   : {s['k1']}")
    print(f"  resolution           : {s['resolution_nm']} nm")
    print(f"  depth of focus       : {s['depth_of_focus_nm']} nm")
    print(f"  7 nm target met      : {s['resolution_target_met']}")
    print(f"  optical transmission : {s['optical_transmission_pct']}%")
    print(f"  throughput           : {s['throughput_wph']} wafers/hr")

    wavelength = r["ai"].get("wavelength_analysis") or {}
    if wavelength.get("tradeoff_table"):
        print("\n  AI WAVELENGTH ANALYSIS -- why 13.5 nm:\n")
        print(f"    {'nm':>5} {'coating':<9} {'R%':>5} {'res':>7} "
              f"{'trans%':>9}  status")
        for row in wavelength["tradeoff_table"]:
            print(f"    {row['wavelength_nm']:>5} {row['coating']:<9} "
                  f"{row['reflectivity_pct']:>5} {row['resolution_nm']:>7} "
                  f"{row['train_transmission_pct']:>9}  {row['status']}")
        print()
        for point in wavelength["points"]:
            print(f"    * {point}")


def honesty(r):
    rule("HONESTY ACCOUNTING")
    s = r["sourcing"]
    print(f"  components   : {s['total_components']}")
    print(f"  sourced      : {s['sourced']} ({s['sourced_pct']}%)")
    print(f"  MODELED      : {s['modeled']}")
    print(f"  by confidence: {s['by_confidence']}")


def api_demo():
    rule("ON-DEMAND ENDPOINTS")

    print("\n  backend.achievable_ranges()")
    ranges = backend.achievable_ranges()
    print(f"    cost       ${ranges['cost_usd']['min']:,.0f} .. "
          f"${ranges['cost_usd']['max']:,.0f}")
    print(f"    efficiency {ranges['efficiency_pct']['min']}% .. "
          f"{ranges['efficiency_pct']['max']}%")
    print(f"    timeline   {ranges['timeline_years']['min']} .. "
          f"{ranges['timeline_years']['max']} years")

    print("\n  backend.solve_for('efficiency', max_cost=150e6, max_timeline=5)")
    print(f"    {backend.solve_for('efficiency', max_cost=150e6, max_timeline=5.0)['explanation']}")

    print("\n  backend.solve_for('cost', min_efficiency=0.65)")
    print(f"    {backend.solve_for('cost', min_efficiency=0.65)['explanation']}")

    print("\n  backend.cost_reduction(target_cost_usd=130e6)")
    advice = backend.cost_reduction(target_cost_usd=130e6)
    for step in advice["pathway"]["steps"]:
        flag = " [HYP]" if step["is_hypothetical"] else ""
        print(f"    {step['step']}. {step['category']:<18} -> "
              f"${step['running_cost_usd']:,.0f} @ "
              f"{step['running_efficiency_pct']}%{flag}")

    print("\n  backend.compare_design_goals()")
    comparison = backend.compare_design_goals()["comparison"]
    print(f"    {'goal':<16} {'cost':>14} {'eff':>7} {'res':>7} {'wph':>7}")
    for goal, row in comparison.items():
        if row.get("infeasible"):
            continue
        print(f"    {goal:<16} ${row['cost_usd']:>13,.0f} "
              f"{row['efficiency_pct']:>6.1f}% {row['resolution_nm']:>6.1f} "
              f"{row['throughput_wph']:>7.0f}")

    print("\n  backend.tradeoff_frontier()")
    frontier = backend.tradeoff_frontier()
    print(f"    {frontier['explanation']}")


SCREENS = {
    1: screen_1, 2: screen_2, 3: screen_3, 4: screen_4, 5: screen_5,
    6: screen_6, 7: screen_7, 8: screen_8, 9: screen_9,
}

if __name__ == "__main__":
    if "--api" in sys.argv:
        api_demo()
        sys.exit(0)

    result = backend.run()
    if not result["ok"]:
        print(f"backend failed: {result['errors']}")
        sys.exit(1)

    wanted = [int(a) for a in sys.argv[1:] if a.isdigit()]
    for number in (wanted or sorted(SCREENS)):
        SCREENS[number](result)

    if not wanted:
        honesty(result)
        print(f"\n  elapsed: {result['meta']['elapsed_seconds']}s")
