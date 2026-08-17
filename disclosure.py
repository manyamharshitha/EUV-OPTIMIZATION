"""
disclosure.py  --  the things we say before a judge asks

Three claims in this project look stronger than they are, and each one loses
credibility the moment a judge discovers it themselves rather than hearing it
from us:

    1. Most of the "domestic alternatives" do not exist.
    2. Per-component costs are modelled, not sourced.
    3. The AI screens may be running deterministic templates, not a model.

The fix is not a slide. A slide gets skipped, and a document gets read after
the demo, if ever. The fix is to compute each disclosure LIVE from the same
data the results come from, put it in the backend payload, and require the
frontend to render it on the same screen as the number it qualifies.

That has a property a slide doesn't: the disclosure cannot drift out of sync
with the claim. If Person A sources ten more components tomorrow, the
citation figure moves on its own. If someone swaps in a configuration with
fewer hypothetical parts, the count follows. Nobody has to remember to update
anything, which means nobody can forget to.

`demo_proof.py` asserts these are present and accurate, so a build that
quietly drops them fails the proof run.

Standard library only.
"""

from __future__ import annotations


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _hypothetical_disclosure(configuration: dict, components: list) -> dict:
    """
    How much of this machine does not exist yet.

    This is the single most dangerous gap between what the demo appears to
    claim and what is true. The tool ranks parts that are specified targets,
    not catalogue items, and a reader who assumes otherwise concludes that
    India currently supplies EUV collectors. It does not.
    """
    chosen = configuration.get("components", []) if configuration else []

    # Two shapes reach here: solver/design_optimizer set an explicit
    # is_hypothetical flag, optimizer.py's configurations carry only the raw
    # supplier string. Check both, or this silently under-reports on the very
    # path the demo actually runs.
    def is_hypothetical(component: dict) -> bool:
        if component.get("is_hypothetical"):
            return True
        return str(component.get("supplier", "")).strip().upper() == "HYPOTHETICAL"

    hypothetical = [c for c in chosen if is_hypothetical(c)]

    catalogue_total = sum(
        1 for c in components
        if str(getattr(c, "supplier", "")).strip().upper() == "HYPOTHETICAL")

    if not chosen:
        headline = "No configuration selected."
        severity = "low"
        say = "No configuration selected."
    elif not hypothetical:
        headline = ("Every part in this configuration is a real, purchasable "
                    "product.")
        severity = "low"
        say = (f"This particular configuration is all real parts. "
               f"{catalogue_total} hypothetical alternatives exist in the "
               f"database but none were selected here.")
    else:
        share = len(hypothetical) / len(chosen) * 100
        headline = (
            f"{len(hypothetical)} of {len(chosen)} parts in this "
            f"configuration ({share:.0f}%) DO NOT EXIST. They are specified "
            f"development targets, not products you can buy today."
        )
        severity = "critical" if share >= 40 else "high"
        say = (
            "None of the domestic alternatives exist yet. They're specified "
            "targets, not catalogue parts. What the optimizer tells you is "
            "which ones would be worth building first."
        )

    return {
        "id": "hypothetical_components",
        "severity": severity,
        "headline": headline,
        "detail": (
            "There is no Indian EUV component industry. Every supplier marked "
            "HYPOTHETICAL is a target specification we defined, not a vendor. "
            "The optimizer's job is to rank which of them would be worth "
            "building first -- that is a legitimate question for a sovereignty "
            "programme, and it is not the same as a procurement plan."
        ),
        "say_this": say,
        "chosen_hypothetical": len(hypothetical),
        "chosen_total": len(chosen),
        "database_hypothetical": catalogue_total,
        "parts": [
            {"category": c.get("category"), "name": c.get("name"),
             "country": c.get("country")}
            for c in hypothetical
        ],
    }


def _cost_basis_disclosure(results: dict, sourcing: dict) -> dict:
    """
    The total is real. The split is ours.

    ASML publishes system prices, not a bill of materials. Presenting a
    per-subsystem figure as if it were sourced is the kind of thing a judge
    with industry background catches instantly, and it costs more credibility
    than the number was ever worth.
    """
    baseline = (results or {}).get("baseline", {})
    total = baseline.get("total_cost_usd", 0)
    sourced_pct = (sourcing or {}).get("sourced_pct", 0.0)

    return {
        "id": "cost_basis",
        "severity": "high",
        "headline": (
            f"The ${total:,.0f} system total is a published figure. The split "
            f"across subsystems is our engineering estimate, not a sourced "
            f"bill of materials."
        ),
        "detail": (
            "No public bill of materials exists for an EUV scanner. ASML "
            "publishes whole-system prices; nobody publishes what the "
            "projection optics cost. We anchored to the real system price and "
            "apportioned it by relative complexity. The total is defensible. "
            "Any individual component cost is an estimate."
        ),
        "say_this": (
            "We can defend the system total -- it's published. The split "
            "across subsystems is ours, and we'd revise it the moment better "
            "data existed."
        ),
        "baseline_total_usd": total,
        "citation_coverage_pct": sourced_pct,
        "coverage_note": (
            f"{sourced_pct}% of components in the database carry a real "
            f"citation. The rest are marked MODELED in the data itself."
        ),
    }


def _ai_backend_disclosure(ai_section: dict) -> dict:
    """
    Whether the AI screens are actually running a model.

    If Ollama is not running, `ai_local_claude.py` returns deterministic
    template text so the demo cannot die mid-pitch. That text is not AI
    output, and presenting it as AI output would be the same category of
    dishonesty as an uncited number.
    """
    status = (ai_section or {}).get("status")
    analysis = (ai_section or {}).get("analysis") or {}
    backend = analysis.get("backend")

    if status != "ok":
        return {
            "id": "ai_backend",
            "severity": "high",
            "headline": "The AI layer is not available in this run.",
            "detail": f"Status: {status}. Every number on screen still comes "
                      f"from deterministic Python and is unaffected.",
            "say_this": "The AI layer isn't running right now. Nothing on "
                        "screen depends on it -- the optimisation is "
                        "deterministic.",
            "backend": None,
            "is_model": False,
        }

    if backend == "local_model":
        return {
            "id": "ai_backend",
            "severity": "low",
            "headline": "AI analysis is generated by a local model, running "
                        "on this machine with no network access.",
            "detail": "Served by Ollama on 127.0.0.1. Model weights are on "
                      "local disk. No API key exists in this codebase.",
            "say_this": "That analysis came from a model running on this "
                        "laptop. Kill the WiFi and it still answers.",
            "backend": "local_model",
            "is_model": True,
        }

    return {
        "id": "ai_backend",
        "severity": "critical",
        "headline": ("These AI panels are RULE-BASED TEMPLATES, not model "
                     "output. No local model is running."),
        "detail": (
            "Ollama is not installed or not running, so ai_local_claude.py "
            "returned deterministic fallback text to keep the demo alive. It "
            "is labelled rule_based in the payload and must be labelled "
            "rule_based on screen. Install Ollama and run "
            "phase2_finetune_local.py to switch this to a real local model."
        ),
        "say_this": (
            "Full disclosure -- that panel is rule-based right now, not the "
            "model. The local model isn't loaded on this machine. Everything "
            "numeric on screen is deterministic Python either way."
        ),
        "backend": "rule_based",
        "is_model": False,
    }


def _resolution_disclosure(simulation: dict) -> dict:
    """We do not reach 7 nm, and we say so on the same screen that shows it."""
    resolution = (simulation or {}).get("resolution_nm")
    met = (simulation or {}).get("resolution_target_met")

    if resolution is None:
        return None

    if met:
        return {
            "id": "resolution_target",
            "severity": "low",
            "headline": f"Computed half-pitch {resolution} nm meets the 7 nm "
                        f"target.",
            "detail": "Rayleigh criterion, single exposure.",
            "say_this": f"{resolution} nm, single exposure.",
        }

    return {
        "id": "resolution_target",
        "severity": "medium",
        "headline": f"This configuration prints {resolution} nm, NOT 7 nm.",
        "detail": (
            "Rayleigh gives k1*lambda/NA. At NA 0.33 that is 14.3 nm; 7 nm "
            "single-exposure would need an NA above the 0.55 High-NA ceiling. "
            "Reaching it in practice means High-NA optics or multi-patterning. "
            "The tool reports the computed number rather than the marketing "
            "node name."
        ),
        "say_this": (
            "We don't hit 7 nm at this NA and we don't claim to -- the tool "
            "prints what the physics gives, which is 14.3 nm."
        ),
    }


def build(result: dict, components: list = ()) -> dict:
    """
    Every disclosure for this run, ordered most-serious first.

    Called by backend.run(). The frontend must render `must_state` before or
    beside the headline numbers -- these are the sentences that have to reach
    a judge from us rather than from their own scepticism.
    """
    configuration = None
    top = (result.get("results") or {}).get("top_configurations") or []
    if top:
        configuration = top[0]

    entries = [
        _hypothetical_disclosure(configuration, list(components)),
        _cost_basis_disclosure(result.get("results"), result.get("sourcing")),
        _ai_backend_disclosure(result.get("ai")),
    ]

    resolution = _resolution_disclosure(result.get("simulation"))
    if resolution:
        entries.append(resolution)

    entries.sort(key=lambda e: SEVERITY_ORDER.get(e["severity"], 9))

    must_state = [e for e in entries
                  if e["severity"] in ("critical", "high")]

    return {
        "count": len(entries),
        "must_state_count": len(must_state),
        "must_state": [
            {"id": e["id"], "severity": e["severity"], "say": e["say_this"]}
            for e in must_state
        ],
        "entries": entries,
        "frontend_contract": (
            "Render every must_state item on the same screen as the number it "
            "qualifies, before the judge reads the number. Do not put these "
            "in a footer, a tooltip, or an about page."
        ),
    }


if __name__ == "__main__":
    import backend
    import optimizer
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    parts = optimizer.load_components(
        os.path.join(here, "data", "components.csv"))

    disclosures = build(backend.run(), parts)

    print("=" * 70)
    print("  DISCLOSURES -- say these before a judge asks")
    print("=" * 70)

    for entry in disclosures["entries"]:
        print(f"\n  [{entry['severity'].upper()}] {entry['headline']}")
        print(f"     say: \"{entry['say_this']}\"")

    print("\n" + "-" * 70)
    print(f"  {disclosures['must_state_count']} of {disclosures['count']} "
          f"must be stated aloud.")
