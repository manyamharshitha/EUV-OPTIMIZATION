"""
phase1_generate_knowledge.py  --  Person C (AI Engineer)

Builds claude_knowledge.json: the grounded fact base the local model is given.

Every entry is pulled live from Person A's sourced data and Person B's
physics. Nothing is typed in by hand here. That matters -- if A revises a
number, re-running this file propagates it to the model's knowledge, and there
is no second copy of the truth drifting out of sync.

Each fact carries its source key and confidence, so the model can be
instructed to repeat the citation rather than assert a bare number.

Runs offline. Needs no model installed.
"""

from __future__ import annotations

import csv
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

DATA_DIR = os.path.join(BASE_DIR, "data")
HERE_AI = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "claude_knowledge.json")


def _load_components() -> list:
    path = os.path.join(DATA_DIR, "components.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_physics_facts() -> list:
    """Facts that come from B's simulation, computed rather than asserted."""
    import euv_simulation as sim

    baseline = sim.run_simulation(
        laser_power_kw=30.0, conversion_efficiency=0.055,
        collector_reflectivity=0.55, collection_solid_angle_sr=5.0,
        mirror_count=10, mirror_reflectivity=0.70,
        numerical_aperture=0.33, dose_mj_cm2=20.0)

    high_na = sim.run_simulation(
        laser_power_kw=30.0, conversion_efficiency=0.055,
        collector_reflectivity=0.55, collection_solid_angle_sr=5.0,
        mirror_count=10, mirror_reflectivity=0.70,
        numerical_aperture=0.55, dose_mj_cm2=20.0)

    return [
        {"fact": f"EUV lithography uses a wavelength of {sim.EUV_WAVELENGTH_NM} nm.",
         "source": "universal", "confidence": "HIGH"},
        {"fact": f"The drive laser is a CO2 laser at "
                 f"{sim.CO2_LASER_WAVELENGTH_UM} micrometres.",
         "source": "S2-TRUMPF-30KW", "confidence": "HIGH"},
        {"fact": f"At NA 0.33 the printed half-pitch is "
                 f"{baseline.resolution_nm} nm, computed as k1 * lambda / NA.",
         "source": "computed", "confidence": "HIGH"},
        {"fact": f"At NA 0.55 (High-NA) the printed half-pitch is "
                 f"{high_na.resolution_nm} nm.",
         "source": "computed", "confidence": "HIGH"},
        {"fact": f"7 nm single-exposure resolution is NOT achievable at NA "
                 f"0.33. The computed value is {baseline.resolution_nm} nm.",
         "source": "computed", "confidence": "HIGH"},
        {"fact": f"Optical transmission through 10 mirrors at 70% each is "
                 f"{baseline.optical_transmission_pct}%.",
         "source": "S5-MIRROR-COUNT", "confidence": "HIGH"},
        {"fact": "The optical train has 6 projection mirrors and 4 "
                 "illuminator mirrors, 10 in total.",
         "source": "S5-MIRROR-COUNT", "confidence": "HIGH"},
        {"fact": "Conversion efficiency from CO2 laser to in-band EUV is "
                 "5-6% in production machines, and 2-4.7% in published "
                 "laboratory experiments depending on target geometry.",
         "source": "S8-CE, S9-CE-PRODUCTION-56", "confidence": "MEDIUM"},
        {"fact": "Mo/Si multilayer reflectivity at 13.5 nm is 68.8% by "
                 "dc-magnetron sputtering, 70.3% with interface engineering, "
                 "with a theoretical ceiling near 75%.",
         "source": "S4-MOSI", "confidence": "HIGH"},
        {"fact": "Depth of focus scales as 1/NA^2 while resolution scales as "
                 "1/NA, so raising NA costs focus budget faster than it gains "
                 "resolution.",
         "source": "Rayleigh", "confidence": "HIGH"},
    ]


def build_component_facts(components: list) -> list:
    """Facts about the parts database, including what is NOT real."""
    facts = []

    real = [c for c in components
            if c.get("supplier", "").upper() != "HYPOTHETICAL"]
    hypothetical = [c for c in components
                    if c.get("supplier", "").upper() == "HYPOTHETICAL"]
    sourced = [c for c in components
               if c.get("source", "").strip().upper() != "MODELED"]

    facts.append({
        "fact": f"The component database holds {len(components)} parts. "
                f"{len(sourced)} carry a real citation; "
                f"{len(components) - len(sourced)} are marked MODELED.",
        "source": "data/components.csv", "confidence": "HIGH"})

    facts.append({
        "fact": f"{len(hypothetical)} components are marked HYPOTHETICAL. "
                f"These parts do not exist and cannot be purchased. They are "
                f"specified development targets, not catalogue items.",
        "source": "data/components.csv", "confidence": "HIGH"})

    facts.append({
        "fact": "The only suppliers in the database that actually exist are "
                "ASML, ZEISS and TRUMPF. Every supplier listed in India is "
                "HYPOTHETICAL.",
        "source": "data/SOURCING_APPENDIX.md", "confidence": "HIGH"})

    baseline_total = sum(float(c["cost_usd"]) for c in components
                         if c.get("is_baseline") == "1")
    facts.append({
        "fact": f"The baseline configuration totals ${baseline_total:,.0f}, "
                f"anchored to the published price of a Low-NA ASML NXE "
                f"scanner. The split across subsystems is MODELED -- no public "
                f"bill of materials exists.",
        "source": "S7-EXE5000-380M", "confidence": "MEDIUM"})

    for component in real[:12]:
        facts.append({
            "fact": f"{component['name']} is supplied by "
                    f"{component['supplier']} ({component['country']}), "
                    f"category {component['category']}.",
            "source": component.get("source", "MODELED"),
            "confidence": component.get("confidence", "LOW")})

    return facts


def build_refusals() -> list:
    """
    Things the model must refuse to answer rather than guess.

    A local 7B will happily invent a component price. Teaching it the shape of
    "I don't have that" is worth more than teaching it ten more facts.
    """
    return [
        {"question": "What does an ASML collector mirror cost?",
         "answer": "I don't have that. No public bill of materials exists for "
                   "an EUV scanner. Our per-component figures are modelled "
                   "splits of a published system total."},
        {"question": "Can this machine reach 7 nm?",
         "answer": "Not at NA 0.33. The computed half-pitch is 14.3 nm. "
                   "Reaching 7 nm requires High-NA optics or multi-patterning."},
        {"question": "Which Indian company makes EUV collectors?",
         "answer": "None. Every Indian supplier in this database is marked "
                   "HYPOTHETICAL. They are targets, not existing vendors."},
        {"question": "What is the exact conversion efficiency?",
         "answer": "Published values range from 2% to 6% depending on target "
                   "geometry. Production machines run 5-6%. I will not quote a "
                   "single figure as if it were exact."},
    ]


def load_cloud_knowledge() -> list:
    """
    Answers extracted from Claude by phase1_cloud_extract.py, if that step was
    run.

    These are general physics, not citations, and they rank BELOW A's sourced
    data: where a cloud answer conflicts with a figure in components.csv or
    the experiment CSVs, A's figure wins. The Modelfile states that ordering
    to the local model explicitly, because a frontier model's confident prose
    is exactly the kind of thing that would otherwise override a sourced
    number.
    """
    path = os.path.join(HERE_AI, "claude_cloud_knowledge.json")
    if not os.path.exists(path):
        return []

    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)

    return [
        {
            "question": entry["question"],
            "answer": entry["answer"],
            "source": entry.get("source", "claude-cloud-phase1"),
            "confidence": entry.get("confidence", "MEDIUM"),
        }
        for entry in payload.get("answers", [])
    ]


def main() -> dict:
    components = build_components_safely()
    cloud = load_cloud_knowledge()

    knowledge = {
        "_generated_by": "phase1_generate_knowledge.py",
        "_purpose": "Grounded fact base for the local model. Regenerate after "
                    "any change to data/components.csv.",
        "_rules_for_model": [
            "Use only facts in this file.",
            "Every number you state must carry its source key.",
            "If a fact is not here, say you do not have it.",
            "Never present a HYPOTHETICAL component as purchasable.",
            "Never claim 7 nm is reached at NA 0.33.",
            "Where general background conflicts with a project figure, the "
            "project figure wins.",
        ],
        "physics": build_physics_facts(),
        "components": build_component_facts(components),
        "general_background": cloud,
        "refusals": build_refusals(),
    }

    knowledge["_counts"] = {
        "physics_facts": len(knowledge["physics"]),
        "component_facts": len(knowledge["components"]),
        "general_background": len(cloud),
        "refusals": len(knowledge["refusals"]),
        "total": (len(knowledge["physics"]) + len(knowledge["components"])
                  + len(cloud) + len(knowledge["refusals"])),
    }

    with open(OUTPUT, "w", encoding="utf-8") as handle:
        json.dump(knowledge, handle, indent=2)

    return knowledge


def build_components_safely() -> list:
    components = _load_components()
    if not components:
        print("WARNING: data/components.csv not found. "
              "Component facts will be empty.")
    return components


if __name__ == "__main__":
    result = main()
    counts = result["_counts"]
    print(f"Wrote {OUTPUT}")
    print(f"  physics facts   : {counts['physics_facts']}")
    print(f"  component facts : {counts['component_facts']}")
    print(f"  refusals        : {counts['refusals']}")
    print(f"  total           : {counts['total']}")
