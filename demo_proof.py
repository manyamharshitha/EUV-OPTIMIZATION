"""
demo_proof.py  --  Person B (Algorithm Engineer), Day 3

The script B runs in front of a judge who says "prove it".

Each check states a claim the pitch makes, tests it, and prints PASS or FAIL.
Nothing here is decorative -- every check corresponds to a sentence someone
will say out loud during the demo.

    python demo_proof.py

Exit code 0 means every claim held.
"""

from __future__ import annotations

import socket
import sys
import time
from itertools import product

import optimizer
import euv_simulation
import particle_manager
import backend


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

class Proof:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.lines = []

    def check(self, claim: str, condition: bool, detail: str = "") -> bool:
        status = "PASS" if condition else "FAIL"
        if condition:
            self.passed += 1
        else:
            self.failed += 1
        self.lines.append((status, claim, detail))
        print(f"  [{status}] {claim}")
        if detail:
            print(f"         {detail}")
        return condition

    def section(self, title: str):
        print(f"\n{title}")
        print("-" * len(title))

    def summary(self) -> int:
        total = self.passed + self.failed
        print("\n" + "=" * 60)
        print(f"  {self.passed}/{total} claims verified")
        if self.failed:
            print(f"  {self.failed} FAILED")
        print("=" * 60)
        return 1 if self.failed else 0


# ---------------------------------------------------------------------------
# Offline enforcement
# ---------------------------------------------------------------------------

class NetworkBlocked(Exception):
    pass


def _block_network():
    """
    Replace socket creation with something that raises.  If any module tries
    to reach the internet during the proof run, it fails loudly instead of
    silently succeeding because the judge's WiFi happened to be on.
    """
    def _refuse(*args, **kwargs):
        raise NetworkBlocked("Network access attempted during offline proof")

    original = socket.socket
    socket.socket = _refuse
    return original


def _restore_network(original):
    socket.socket = original


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def prove_exhaustive_search(proof: Proof, components: list):
    proof.section("CLAIM 1 -- the optimiser evaluates every combination")

    grouped = optimizer.group_by_category(components)
    expected = 1
    for alternatives in grouped.values():
        expected *= len(alternatives)

    # Count the product independently of optimizer's own arithmetic.
    counted = sum(1 for _ in product(*grouped.values()))

    proof.check(
        "Combination count is the full Cartesian product",
        counted == expected,
        f"{len(grouped)} categories -> {counted:,} combinations",
    )

    outcome = optimizer.optimize(components, optimizer.Constraints())
    proof.check(
        "Optimiser reports the same total it actually searched",
        outcome["combinations_evaluated"] == expected,
        f"reported {outcome['combinations_evaluated']:,}, expected {expected:,}",
    )

    proof.check(
        "Feasible + infeasible accounts for every combination",
        outcome["feasible_count"] + outcome["infeasible_count"] == expected,
        f"{outcome['feasible_count']:,} feasible + "
        f"{outcome['infeasible_count']:,} rejected",
    )


def prove_constraints_honoured(proof: Proof, components: list):
    proof.section("CLAIM 2 -- returned answers never violate the constraints")

    budget = 150_000_000.0
    min_eff = 0.45
    max_years = 6.0

    outcome = optimizer.optimize(
        components,
        optimizer.Constraints(max_budget_usd=budget,
                              min_efficiency=min_eff,
                              max_timeline_years=max_years),
    )

    tops = outcome["top_configurations"]
    proof.check("A feasible answer exists at these constraints", bool(tops))

    if tops:
        proof.check(
            "Every returned configuration is under budget",
            all(config["total_cost_usd"] <= budget for config in tops),
            f"max returned ${max(c['total_cost_usd'] for c in tops):,.0f} "
            f"vs limit ${budget:,.0f}",
        )
        proof.check(
            "Every returned configuration meets the efficiency floor",
            all(config["overall_efficiency"] >= min_eff for config in tops),
        )
        proof.check(
            "Every returned configuration meets the timeline limit",
            all(config["timeline_years"] <= max_years for config in tops),
        )
        proof.check(
            "Results are ranked best-score-first",
            all(tops[i]["score"] >= tops[i + 1]["score"] for i in range(len(tops) - 1)),
        )


def prove_impossible_constraints_fail_cleanly(proof: Proof, components: list):
    proof.section("CLAIM 3 -- impossible constraints return a message, not a crash")

    outcome = optimizer.optimize(
        components, optimizer.Constraints(max_budget_usd=1.0)
    )
    proof.check(
        "A $1 budget yields zero configurations and no exception",
        outcome["top_configurations"] == [] and "message" in outcome,
    )

    result = backend.run(budget_usd=1.0)
    proof.check(
        "backend.run() survives an impossible budget",
        result["ok"] and result["results"]["top_configurations"] == [],
    )
    proof.check(
        "Sliders are still returned so the judge can recover",
        result["interactivity"] is not None,
    )


def prove_determinism(proof: Proof, components: list):
    proof.section("CLAIM 4 -- the same input always gives the same answer")

    first = optimizer.optimize(components, optimizer.Constraints(max_budget_usd=180e6))
    second = optimizer.optimize(components, optimizer.Constraints(max_budget_usd=180e6))

    ids_first = [[c["component_id"] for c in config["components"]]
                 for config in first["top_configurations"]]
    ids_second = [[c["component_id"] for c in config["components"]]
                  for config in second["top_configurations"]]

    proof.check("Two identical runs return identical rankings", ids_first == ids_second)

    scores_first = [config["score"] for config in first["top_configurations"]]
    scores_second = [config["score"] for config in second["top_configurations"]]
    proof.check("Scores are bit-identical across runs", scores_first == scores_second)


def prove_physics(proof: Proof):
    proof.section("CLAIM 5 -- the physics is real physics")

    # Rayleigh: halving NA should double the printed feature size.
    coarse = euv_simulation.rayleigh_resolution(0.25)
    fine = euv_simulation.rayleigh_resolution(0.50)
    proof.check(
        "Resolution scales as 1/NA (Rayleigh)",
        abs(coarse / fine - 2.0) < 1e-9,
        f"NA 0.25 -> {coarse:.2f} nm, NA 0.50 -> {fine:.2f} nm",
    )

    # DOF scales as 1/NA^2.
    dof_low = euv_simulation.depth_of_focus(0.25)
    dof_high = euv_simulation.depth_of_focus(0.50)
    proof.check(
        "Depth of focus scales as 1/NA^2",
        abs(dof_low / dof_high - 4.0) < 1e-9,
        f"{dof_low:.1f} nm vs {dof_high:.1f} nm",
    )

    # Each additional mirror must reduce throughput.
    ten = euv_simulation.optical_train_transmission(10, 0.70)
    eleven = euv_simulation.optical_train_transmission(11, 0.70)
    proof.check(
        "Every extra mirror costs transmission",
        eleven < ten,
        f"10 mirrors {ten * 100:.2f}%, 11 mirrors {eleven * 100:.2f}%",
    )

    # Test against the published anchor conditions, not arbitrary ones:
    # 30 kW drive, 5.5% CE, 20 mJ/cm2 dose -- the configuration ASML quotes
    # 125-150 wph for [S1, S13].  The previous version of this check used
    # 20 kW at the default 30 mJ/cm2 dose, which is not a published operating
    # point, so the band it asserted could not actually validate anything.
    result = euv_simulation.run_simulation(
        laser_power_kw=30.0, conversion_efficiency=0.055,
        collector_reflectivity=0.55, collection_solid_angle_sr=5.0,
        mirror_count=10, mirror_reflectivity=0.70, numerical_aperture=0.33,
        dose_mj_cm2=20.0,
    )
    proof.check(
        "Published NXE:3400B conditions give 120-180 wafers/hour",
        120.0 <= result.throughput_wph <= 180.0,
        f"{result.throughput_wph:.0f} wph (ASML publishes 125-150 for this "
        f"configuration; we run ~10% high because we model 70% mirrors "
        f"rather than the 65% fleet-average behind that figure)",
    )
    proof.check(
        "NA 0.33 prints in the 13-16 nm half-pitch range",
        13.0 <= result.resolution_nm <= 16.0,
        f"{result.resolution_nm:.2f} nm",
    )

    # High-NA must beat standard NA.
    high_na = euv_simulation.run_simulation(
        laser_power_kw=20.0, conversion_efficiency=0.05,
        collector_reflectivity=0.55, collection_solid_angle_sr=5.0,
        mirror_count=10, mirror_reflectivity=0.70, numerical_aperture=0.55,
    )
    proof.check(
        "High-NA (0.55) prints finer than standard NA (0.33)",
        high_na.resolution_nm < result.resolution_nm,
        f"{high_na.resolution_nm:.2f} nm vs {result.resolution_nm:.2f} nm",
    )

    # Rejects unphysical input rather than returning nonsense.
    for bad_call, label in [
        (lambda: euv_simulation.plasma_euv_power(-5, 0.05), "negative laser power"),
        (lambda: euv_simulation.plasma_euv_power(20, 1.5), "conversion efficiency above 100%"),
        (lambda: euv_simulation.rayleigh_resolution(0.0), "zero numerical aperture"),
    ]:
        try:
            bad_call()
            proof.check(f"Rejects {label}", False, "no exception raised")
        except ValueError:
            proof.check(f"Rejects {label}", True)


def prove_contamination(proof: Proof):
    proof.section("CLAIM 6 -- the contamination model behaves correctly")

    clean = particle_manager.assess(iso_class=1, resolution_nm=7.0)
    dirty = particle_manager.assess(iso_class=7, resolution_nm=7.0)

    proof.check(
        "A cleaner room yields better than a dirtier one",
        clean.yield_pct > dirty.yield_pct,
        f"ISO 1: {clean.yield_pct:.2f}%  vs  ISO 7: {dirty.yield_pct:.2f}%",
    )
    proof.check(
        "A cleaner room costs more to operate",
        clean.annual_operating_cost_usd > dirty.annual_operating_cost_usd,
    )

    # ISO 14644-1 anchor: class 5 permits 100,000 particles/m3 at 0.1 um.
    limit = particle_manager.iso_particle_limit(5, 0.1)
    proof.check(
        "ISO formula reproduces the published class 5 limit at 0.1 um",
        abs(limit - 100_000.0) < 1.0,
        f"computed {limit:,.0f} /m3, standard says 100,000",
    )

    proof.check(
        "Finer features imply smaller killer particles",
        particle_manager.killer_particle_size(7.0)
        < particle_manager.killer_particle_size(28.0),
    )

    comparison = particle_manager.compare_all_classes(7.0)
    proof.check(
        "All nine ISO classes are costed and ranked",
        len(comparison) == 9
        and all(comparison[i]["total_cleanliness_cost_usd"]
                <= comparison[i + 1]["total_cleanliness_cost_usd"]
                for i in range(len(comparison) - 1)),
    )


def prove_backend_contract(proof: Proof):
    proof.section("CLAIM 7 -- backend.run() honours its contract with the frontend")

    required = ["meta", "user_input", "results", "visualization", "interactivity",
                "particles", "cleanliness", "ai", "data_learning", "simulation",
                "sourcing", "errors", "ok"]

    result = backend.run()
    missing = [key for key in required if key not in result]
    proof.check("Every contracted top-level key is present", not missing,
                f"missing: {missing}" if missing else "13/13 keys")

    proof.check("Run reports success", result["ok"] is True)
    proof.check("No errors on the default run", result["errors"] == [],
                str(result["errors"]) if result["errors"] else "")
    proof.check("Exactly 5 configurations returned",
                len(result["results"]["top_configurations"]) == 5)
    proof.check("Charts are populated",
                bool(result["visualization"]["cost_bar"])
                and bool(result["visualization"]["cost_pie"])
                and bool(result["visualization"]["timeline"]))
    proof.check("Parts mapping is populated",
                bool(result["visualization"]["parts_mapping"]))
    proof.check("Missing AI modules degrade gracefully",
                result["ai"]["status"] in ("ok", "unavailable", "error"),
                f"AI status: {result['ai']['status']}")


def prove_slider_sweep(proof: Proof):
    proof.section("CLAIM 8 -- any slider position a judge can reach still works")

    failures = []
    runs = 0
    slowest = 0.0

    budgets = [80e6, 120e6, 160e6, 200e6, 260e6]
    efficiencies = [0.10, 0.30, 0.50, 0.65]
    timelines = [3.0, 5.0, 8.0]

    for budget in budgets:
        for efficiency in efficiencies:
            for timeline in timelines:
                runs += 1
                started = time.perf_counter()
                try:
                    result = backend.run(budget_usd=budget,
                                         min_efficiency=efficiency,
                                         max_timeline_years=timeline)
                    if not result["ok"]:
                        failures.append((budget, efficiency, timeline, result["errors"]))
                except Exception as exc:
                    failures.append((budget, efficiency, timeline, repr(exc)))
                slowest = max(slowest, time.perf_counter() - started)

    proof.check(
        f"All {runs} slider combinations complete without error",
        not failures,
        f"{len(failures)} failures" if failures else f"slowest run {slowest:.2f}s",
    )
    proof.check(
        "Worst-case response stays under 3 seconds",
        slowest < 3.0,
        f"{slowest:.2f}s",
    )


def prove_offline(proof: Proof):
    proof.section("CLAIM 9 -- the demo needs no internet")

    original = _block_network()
    try:
        result = backend.run()
        proof.check(
            "Full pipeline runs with all sockets disabled",
            result["ok"] is True,
            "no network call was attempted",
        )
    except NetworkBlocked as exc:
        proof.check("Full pipeline runs with all sockets disabled", False, str(exc))
    finally:
        _restore_network(original)


def prove_sourcing_honesty(proof: Proof):
    proof.section("CLAIM 10 -- we report our own citation coverage honestly")

    result = backend.run()
    sourcing = result["sourcing"]

    proof.check(
        "Every component is accounted for as sourced or MODELED",
        sourcing["sourced"] + sourcing["modeled"] == sourcing["total_components"],
        f"{sourcing['sourced']} sourced / {sourcing['modeled']} modelled "
        f"({sourcing['sourced_pct']}% cited)",
    )

    if sourcing["sourced_pct"] < 50.0:
        print(f"\n  NOTE: only {sourcing['sourced_pct']}% of components carry a")
        print("  citation. That is Person A's Day 1-2 job. Until it rises, the")
        print("  honesty slide must say so out loud.")


def prove_disclosures(proof: Proof):
    """
    The project discloses its own weak points, on every run.

    A disclosure that can be silently dropped is not a safeguard. These checks
    fail the build if the payload stops carrying them, or if the count stops
    matching what is actually in the configuration.
    """
    proof.section("CLAIM 11 -- the tool states its own limitations")

    import optimizer as _optimizer
    parts = _optimizer.load_components(backend.DEFAULT_COMPONENTS_CSV)

    result = backend.run()
    disclosures = result.get("disclosure", {})

    proof.check(
        "Every run carries a disclosure block",
        bool(disclosures.get("entries")),
        f"{disclosures.get('count', 0)} disclosures, "
        f"{disclosures.get('must_state_count', 0)} must be stated aloud",
    )

    ids = {e["id"] for e in disclosures.get("entries", [])}
    for required in ("hypothetical_components", "cost_basis", "ai_backend"):
        proof.check(f"Discloses {required}", required in ids)

    # The hypothetical count must match the configuration, not a stored
    # number. A cost-focused run selects mostly non-existent parts, and the
    # disclosure has to follow it there.
    cheap = backend.run(weight_cost=0.9, weight_efficiency=0.05,
                        weight_time=0.05, min_efficiency=0.30)
    entry = next(e for e in cheap["disclosure"]["entries"]
                 if e["id"] == "hypothetical_components")

    chosen = cheap["results"]["top_configurations"][0]["components"]
    actual = sum(1 for c in chosen
                 if str(c.get("supplier", "")).strip().upper() == "HYPOTHETICAL")

    proof.check(
        "Hypothetical-part count matches the chosen configuration",
        entry["chosen_hypothetical"] == actual,
        f"disclosed {entry['chosen_hypothetical']}, actual {actual} "
        f"of {len(chosen)}",
    )

    proof.check(
        "A mostly-hypothetical configuration is flagged critical",
        entry["severity"] == "critical" if actual / len(chosen) >= 0.4 else True,
        f"severity {entry['severity']} at {actual}/{len(chosen)} hypothetical",
    )

    # The AI disclosure must track the real backend, not a hard-coded string.
    ai_entry = next(e for e in disclosures["entries"] if e["id"] == "ai_backend")
    reported = (result.get("ai") or {}).get("analysis", {}).get("backend")
    proof.check(
        "AI disclosure matches the backend actually used",
        ai_entry["backend"] == reported,
        f"disclosed {ai_entry['backend']!r}, actual {reported!r}",
    )

    if not ai_entry["is_model"]:
        print("\n  NOTE: the AI panels are rule-based in this run, not model")
        print("  output. Install Ollama and run phase2_finetune_local.py to")
        print("  change that. Until then the frontend MUST show the label.")


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("  EUV COMPONENTS OPTIMIZER -- PROOF RUN")
    print("  Person B / algorithm verification")
    print("=" * 60)

    proof = Proof()

    try:
        components = optimizer.load_components(backend.DEFAULT_COMPONENTS_CSV)
    except Exception as exc:
        print(f"\nFATAL: could not load components -- {exc}")
        return 1

    print(f"\nLoaded {len(components)} components from "
          f"{backend.DEFAULT_COMPONENTS_CSV}")

    prove_exhaustive_search(proof, components)
    prove_constraints_honoured(proof, components)
    prove_impossible_constraints_fail_cleanly(proof, components)
    prove_determinism(proof, components)
    prove_physics(proof)
    prove_contamination(proof)
    prove_backend_contract(proof)
    prove_slider_sweep(proof)
    prove_offline(proof)
    prove_sourcing_honesty(proof)
    prove_disclosures(proof)

    return proof.summary()


if __name__ == "__main__":
    sys.exit(main())
