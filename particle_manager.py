"""
particle_manager.py  --  Person B (Algorithm Engineer)

Contamination modelling for EUV manufacture and operation.

Why this module exists: at 13.5 nm there is no pellicle solution as forgiving
as DUV's, and a particle roughly half the printed feature size is a killer
defect.  Cleanliness is not housekeeping in EUV -- it is a first-order cost
and yield driver, which is exactly the argument this screen has to make.

Standards modelled:
  * ISO 14644-1 cleanroom classification
  * Murphy's yield model for random defect limited yield

Pure standard library.  Reads particle_limits.json (Person A's file) if it is
present, otherwise falls back to the ISO standard formula, so B is never
blocked waiting on the data handoff.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, asdict, field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# A particle is a killer defect once it reaches this fraction of the printed
# half-pitch.  Widely used rule of thumb in defect metrology.
KILLER_DEFECT_RATIO = 0.5

# Representative 300 mm logic die footprint, cm^2.  CALIBRATED.
DEFAULT_DIE_AREA_CM2 = 1.0

# Annual cleanroom operating cost per square metre, by ISO class, USD.
# Cost climbs steeply because air change rate, filtration and gowning
# discipline all escalate.  CALIBRATED -- Person A to source or flag [MODELED].
CLEANROOM_ANNUAL_COST_PER_M2 = {
    1: 42000.0,
    2: 26000.0,
    3: 15500.0,
    4: 9200.0,
    5: 5400.0,
    6: 3100.0,
    7: 1800.0,
    8: 1050.0,
    9: 600.0,
}

# One-off build cost per square metre, by ISO class, USD.  CALIBRATED.
CLEANROOM_BUILD_COST_PER_M2 = {
    1: 155000.0,
    2: 98000.0,
    3: 62000.0,
    4: 39000.0,
    5: 24500.0,
    6: 15500.0,
    7: 9800.0,
    8: 6200.0,
    9: 3900.0,
}

RISK_BANDS = (
    (0.00, 0.02, "MINIMAL",  "Within EUV production norms."),
    (0.02, 0.10, "LOW",      "Acceptable; routine monitoring."),
    (0.10, 0.25, "MODERATE", "Yield impact measurable. Tighten gowning and air changes."),
    (0.25, 0.50, "HIGH",     "Significant yield loss. Cleanroom class upgrade indicated."),
    (0.50, 1.01, "CRITICAL", "Not viable for production at this class."),
)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ContaminationReport:
    iso_class: int
    cleanroom_area_m2: float

    killer_particle_size_um: float
    particles_per_m3: float
    surface_deposition_per_cm2_per_hr: float

    defect_density_per_cm2: float
    die_area_cm2: float
    yield_pct: float
    yield_loss_pct: float

    risk_level: str
    risk_note: str

    build_cost_usd: float
    annual_operating_cost_usd: float
    cost_of_yield_loss_usd: float
    total_cleanliness_cost_usd: float

    recommended_iso_class: int
    recommendation: str

    breakdown: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# ISO 14644-1
# ---------------------------------------------------------------------------

def iso_particle_limit(iso_class: int, particle_size_um: float) -> float:
    """
    ISO 14644-1 concentration limit, particles per cubic metre of size >= D.

        Cn = 10^N * (0.1 / D)^2.08

    Valid for classes 1-9 and particle sizes from 0.1 um upward.
    """
    if iso_class not in range(1, 10):
        raise ValueError("iso_class must be 1..9")
    if particle_size_um < 0.1:
        particle_size_um = 0.1

    return (10.0 ** iso_class) * ((0.1 / particle_size_um) ** 2.08)


def killer_particle_size(resolution_nm: float) -> float:
    """Smallest particle that prints as a defect, in micrometres."""
    return (resolution_nm * KILLER_DEFECT_RATIO) / 1000.0


def load_particle_limits(path: str = "particle_limits.json") -> dict:
    """
    Person A owns particle_limits.json.  If it has not been handed over yet,
    return an empty dict and let the ISO formula supply the numbers.

    B never writes this file -- read only.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# Deposition and yield
# ---------------------------------------------------------------------------

def surface_deposition_rate(particles_per_m3: float,
                            deposition_velocity_cm_s: float = 0.03) -> float:
    """
    Particles landing per cm^2 per hour.

    Gravitational settling plus diffusion, collapsed into a single deposition
    velocity.  0.03 cm/s is a standard figure for sub-micron particles in
    laminar downflow.  CALIBRATED.
    """
    particles_per_cm3 = particles_per_m3 / 1.0e6
    return particles_per_cm3 * deposition_velocity_cm_s * 3600.0


def murphy_yield(defect_density_per_cm2: float, die_area_cm2: float) -> float:
    """
    Murphy's model for random-defect-limited yield:

        Y = ((1 - e^(-A*D)) / (A*D))^2

    Assumes defects are randomly distributed across the wafer.  Returns a
    fraction between 0 and 1.
    """
    ad = defect_density_per_cm2 * die_area_cm2
    if ad <= 0:
        return 1.0
    return ((1.0 - math.exp(-ad)) / ad) ** 2


def classify_risk(yield_loss_fraction: float) -> tuple:
    for low, high, level, note in RISK_BANDS:
        if low <= yield_loss_fraction < high:
            return level, note
    return "CRITICAL", "Not viable for production at this class."


def recommend_iso_class(resolution_nm: float,
                        die_area_cm2: float,
                        exposure_hours: float,
                        max_acceptable_yield_loss: float = 0.10) -> int:
    """
    Cheapest (highest-numbered) ISO class that still holds yield loss under
    the acceptable threshold.  Walks from dirtiest to cleanest and stops at
    the first class that passes.
    """
    for candidate in range(9, 0, -1):
        report = assess(
            iso_class=candidate,
            resolution_nm=resolution_nm,
            die_area_cm2=die_area_cm2,
            exposure_hours=exposure_hours,
            _skip_recommendation=True,
        )
        if report.yield_loss_pct / 100.0 <= max_acceptable_yield_loss:
            return candidate
    return 1


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def assess(iso_class: int,
           resolution_nm: float,
           die_area_cm2: float = DEFAULT_DIE_AREA_CM2,
           cleanroom_area_m2: float = 2000.0,
           exposure_hours: float = 1.0,
           wafer_value_usd: float = 16000.0,
           annual_wafer_volume: int = 50000,
           limits_path: str = "particle_limits.json",
           _skip_recommendation: bool = False) -> ContaminationReport:
    """
    Full contamination assessment for one cleanroom class and one printed
    resolution.  Everything the Particle Management and Cleanliness screens
    need comes out of here.
    """
    limits = load_particle_limits(limits_path)

    killer_um = killer_particle_size(resolution_nm)

    override = limits.get(str(iso_class), {}).get("particles_per_m3")
    if override is not None:
        particles_m3 = float(override)
    else:
        particles_m3 = iso_particle_limit(iso_class, killer_um)

    deposition = surface_deposition_rate(particles_m3)
    defect_density = deposition * max(exposure_hours, 0.0)

    yield_fraction = murphy_yield(defect_density, die_area_cm2)
    yield_loss_fraction = 1.0 - yield_fraction

    risk_level, risk_note = classify_risk(yield_loss_fraction)

    build_cost = CLEANROOM_BUILD_COST_PER_M2[iso_class] * cleanroom_area_m2
    annual_cost = CLEANROOM_ANNUAL_COST_PER_M2[iso_class] * cleanroom_area_m2
    yield_loss_cost = yield_loss_fraction * wafer_value_usd * annual_wafer_volume

    if _skip_recommendation:
        recommended = iso_class
        recommendation = ""
    else:
        recommended = recommend_iso_class(resolution_nm, die_area_cm2, exposure_hours)
        if recommended == iso_class:
            recommendation = f"ISO {iso_class} is the correct class for {resolution_nm:.1f} nm."
        elif recommended < iso_class:
            recommendation = (
                f"Upgrade to ISO {recommended}. The extra "
                f"${(CLEANROOM_ANNUAL_COST_PER_M2[recommended] - CLEANROOM_ANNUAL_COST_PER_M2[iso_class]) * cleanroom_area_m2:,.0f}/yr "
                f"is cheaper than the yield loss at ISO {iso_class}."
            )
        else:
            recommendation = (
                f"ISO {iso_class} is over-specified. ISO {recommended} holds yield and saves "
                f"${(CLEANROOM_ANNUAL_COST_PER_M2[iso_class] - CLEANROOM_ANNUAL_COST_PER_M2[recommended]) * cleanroom_area_m2:,.0f}/yr."
            )

    breakdown = [
        {"stage": "Killer particle size", "value": round(killer_um, 5), "unit": "um"},
        {"stage": "Airborne concentration", "value": round(particles_m3, 1), "unit": "particles/m3"},
        {"stage": "Surface deposition", "value": round(deposition, 5), "unit": "per cm2/hr"},
        {"stage": "Defect density", "value": round(defect_density, 5), "unit": "per cm2"},
        {"stage": "Die yield", "value": round(yield_fraction * 100.0, 2), "unit": "%"},
    ]

    return ContaminationReport(
        iso_class=iso_class,
        cleanroom_area_m2=cleanroom_area_m2,
        killer_particle_size_um=round(killer_um, 5),
        particles_per_m3=round(particles_m3, 2),
        surface_deposition_per_cm2_per_hr=round(deposition, 6),
        defect_density_per_cm2=round(defect_density, 6),
        die_area_cm2=die_area_cm2,
        yield_pct=round(yield_fraction * 100.0, 3),
        yield_loss_pct=round(yield_loss_fraction * 100.0, 3),
        risk_level=risk_level,
        risk_note=risk_note,
        build_cost_usd=round(build_cost, 2),
        annual_operating_cost_usd=round(annual_cost, 2),
        cost_of_yield_loss_usd=round(yield_loss_cost, 2),
        total_cleanliness_cost_usd=round(annual_cost + yield_loss_cost, 2),
        recommended_iso_class=recommended,
        recommendation=recommendation,
        breakdown=breakdown,
    )


def compare_all_classes(resolution_nm: float,
                        die_area_cm2: float = DEFAULT_DIE_AREA_CM2,
                        cleanroom_area_m2: float = 2000.0,
                        exposure_hours: float = 1.0) -> list:
    """
    Every ISO class scored side by side, cheapest total cost first.
    Feeds the Cleanliness comparison chart.
    """
    rows = []
    for iso_class in range(1, 10):
        report = assess(
            iso_class=iso_class,
            resolution_nm=resolution_nm,
            die_area_cm2=die_area_cm2,
            cleanroom_area_m2=cleanroom_area_m2,
            exposure_hours=exposure_hours,
            _skip_recommendation=True,
        )
        rows.append({
            "iso_class": iso_class,
            "yield_pct": report.yield_pct,
            "risk_level": report.risk_level,
            "annual_operating_cost_usd": report.annual_operating_cost_usd,
            "cost_of_yield_loss_usd": report.cost_of_yield_loss_usd,
            "total_cleanliness_cost_usd": report.total_cleanliness_cost_usd,
        })

    rows.sort(key=lambda row: row["total_cleanliness_cost_usd"])
    return rows


if __name__ == "__main__":
    report = assess(iso_class=3, resolution_nm=7.0)
    for row in report.breakdown:
        print(f"{row['stage']:<28} {row['value']:>14} {row['unit']}")
    print()
    print(f"Risk       : {report.risk_level} -- {report.risk_note}")
    print(f"Recommend  : {report.recommendation}")
