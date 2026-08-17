"""
euv_simulation.py  --  Person B (Algorithm Engineer)

Physics chain for an LPP (laser-produced plasma) EUV source:

    CO2 laser  ->  tin droplet  ->  plasma  ->  13.5 nm EUV  ->  optics  ->  wafer

Every formula here is standard lithography physics, not invented.  Where a
constant is a calibration factor rather than a first-principles quantity it is
marked CALIBRATED in the comment, so Person A can source it or flag it
[MODELED] in the sourcing appendix.

Pure standard library.  No numpy, no scipy.  The demo must run on a judge's
laptop with the WiFi switched off.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

EUV_WAVELENGTH_NM = 13.5        # in-band EUV, Mo/Si multilayer reflectance peak
CO2_LASER_WAVELENGTH_UM = 10.6  # drive laser
WAFER_DIAMETER_MM = 300.0
TIN_IONISATION_STATES = (8, 14)  # Sn8+ .. Sn14+ radiate the 13.5 nm band

# Rayleigh coefficients.  k1 is process-dependent; 0.35 is a realistic
# single-exposure production value (theoretical floor is 0.25).
DEFAULT_K1 = 0.35
DEFAULT_K2 = 0.50

# Fraction of the exposure hour actually spent exposing, after wafer load,
# stepping between fields, alignment and metrology.  CALIBRATED against the
# published anchor: 245 W at intermediate focus, 20 mJ/cm2 dose, 140 wafers
# per hour achieved [S1, S13].  With 1.3% train transmission that is 3.19 W at
# the wafer, a theoretical ceiling of 812 wph, so 140/812 = 0.172.
#
# Was 0.30, which had been calibrated at 30 mJ/cm2 while ASML quotes
# throughput at 20 mJ/cm2 -- that mismatch inflated throughput by ~2.8x.
# Found by Person A's validation pass, see data/VALIDATION_REPORT.md.
SCAN_DUTY_FACTOR = 0.17

# Losses between the collector and the intermediate focus that the geometric
# model does not capture: IF aperture clipping, debris-mitigation hardware in
# the beam path, and collector reflectivity degradation over service life.
#
# CALIBRATED.  Purely geometric collection gives 361 W for a 30 kW drive at
# 5.5% CE, while real machines with that drive laser deliver ~250 W at IF, so
# the lumped factor is 250/361 = 0.69.  This is a fitted constant standing in
# for several unmodelled effects, not a measured quantity -- Person A has it
# flagged MODELED in the sourcing appendix.
#
# It exists as its own term rather than being absorbed into SCAN_DUTY_FACTOR
# deliberately.  Burying a physics error inside a throughput calibration is
# what made the original 2.8x throughput overestimate hard to see.
IF_COLLECTION_LOSS = 0.69

# Reflectivity of the EUV reticle (Mo/Si multilayer + absorber pattern).
MASK_REFLECTIVITY = 0.60

# Spectral purity filter transmission (rejects out-of-band and 10.6 um light).
SPF_TRANSMISSION = 0.90


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """One full pass down the optical chain.  Every field is display-ready."""

    # Source
    laser_power_kw: float
    conversion_efficiency_pct: float
    euv_generated_w: float

    # Collector / intermediate focus
    collector_efficiency_pct: float
    intermediate_focus_power_w: float

    # Optical train
    mirror_count: int
    mirror_reflectivity_pct: float
    optical_transmission_pct: float
    wafer_plane_power_w: float

    # Imaging
    numerical_aperture: float
    k1: float
    resolution_nm: float
    depth_of_focus_nm: float
    resolution_target_met: bool

    # Productivity
    dose_mj_cm2: float
    throughput_wph: float

    # Narrative for the UI
    stages: list

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Individual physics steps
# ---------------------------------------------------------------------------

def plasma_euv_power(laser_power_kw: float, conversion_efficiency: float) -> float:
    """
    In-band EUV radiated by the tin plasma, in watts.

    Conversion efficiency is the single most important number in the whole
    machine: the fraction of drive-laser energy that emerges as 13.5 nm light
    inside the 2% reflectance bandwidth of the Mo/Si mirrors.  Production
    sources sit around 5-6%.
    """
    if laser_power_kw <= 0:
        raise ValueError("laser_power_kw must be positive")
    if not 0 < conversion_efficiency < 1:
        raise ValueError("conversion_efficiency must be a fraction between 0 and 1")
    return laser_power_kw * 1000.0 * conversion_efficiency


def intermediate_focus_power(euv_watts: float,
                             collector_reflectivity: float,
                             collection_solid_angle_sr: float) -> float:
    """
    Power delivered to the intermediate focus (IF) -- the industry's standard
    quoting point for "source power".

    The plasma radiates into the full 4*pi steradians.  The collector mirror
    only subtends part of that, and reflects only part of what it catches.
    """
    if not 0 < collector_reflectivity < 1:
        raise ValueError("collector_reflectivity must be between 0 and 1")

    full_sphere_sr = 4.0 * math.pi
    if not 0 < collection_solid_angle_sr <= full_sphere_sr:
        raise ValueError("collection_solid_angle_sr out of physical range")

    geometric_fraction = collection_solid_angle_sr / full_sphere_sr
    return (euv_watts * geometric_fraction * collector_reflectivity
            * IF_COLLECTION_LOSS)


def optical_train_transmission(mirror_count: int,
                               mirror_reflectivity: float) -> float:
    """
    Fraction of IF power surviving to the wafer.

    This is the brutal part of EUV.  There are no transmissive lenses at
    13.5 nm -- everything is a mirror, and every mirror costs you.  Ten
    mirrors at 70% each leaves under 3%.
    """
    if mirror_count < 1:
        raise ValueError("mirror_count must be at least 1")
    if not 0 < mirror_reflectivity < 1:
        raise ValueError("mirror_reflectivity must be between 0 and 1")

    return (mirror_reflectivity ** mirror_count) * MASK_REFLECTIVITY * SPF_TRANSMISSION


def rayleigh_resolution(numerical_aperture: float, k1: float = DEFAULT_K1) -> float:
    """Smallest printable half-pitch, nm.  CD = k1 * lambda / NA."""
    if not 0 < numerical_aperture < 1:
        raise ValueError("numerical_aperture must be between 0 and 1")
    return k1 * EUV_WAVELENGTH_NM / numerical_aperture


def depth_of_focus(numerical_aperture: float, k2: float = DEFAULT_K2) -> float:
    """Usable focus window, nm.  DOF = k2 * lambda / NA^2.

    Note the NA^2: raising NA sharpens the image but collapses the focus
    budget, which is exactly why High-NA tools are hard.
    """
    if not 0 < numerical_aperture < 1:
        raise ValueError("numerical_aperture must be between 0 and 1")
    return k2 * EUV_WAVELENGTH_NM / (numerical_aperture ** 2)


def throughput_wph(wafer_plane_power_w: float, dose_mj_cm2: float) -> float:
    """
    Wafers per hour.

    Energy needed per wafer = dose * wafer area.  Divide available power by
    that, convert to hours, then derate by the scan duty factor for the time
    the tool spends not exposing.
    """
    if wafer_plane_power_w <= 0 or dose_mj_cm2 <= 0:
        return 0.0

    radius_cm = (WAFER_DIAMETER_MM / 10.0) / 2.0
    wafer_area_cm2 = math.pi * radius_cm ** 2
    energy_per_wafer_mj = dose_mj_cm2 * wafer_area_cm2

    power_mj_per_s = wafer_plane_power_w * 1000.0
    wafers_per_second = power_mj_per_s / energy_per_wafer_mj

    return wafers_per_second * 3600.0 * SCAN_DUTY_FACTOR


# ---------------------------------------------------------------------------
# Full chain
# ---------------------------------------------------------------------------

def run_simulation(laser_power_kw: float,
                   conversion_efficiency: float,
                   collector_reflectivity: float,
                   collection_solid_angle_sr: float,
                   mirror_count: int,
                   mirror_reflectivity: float,
                   numerical_aperture: float,
                   dose_mj_cm2: float = 30.0,
                   k1: float = DEFAULT_K1,
                   target_resolution_nm: float = 7.0) -> SimulationResult:
    """
    Run the whole chain and return everything the frontend needs to draw the
    EUV Simulation screen and the Resolution Proof screen.

    `stages` is an ordered list of (label, value, unit) suitable for rendering
    as an animated pipeline -- laser in on the left, wafer on the right.
    """
    euv_w = plasma_euv_power(laser_power_kw, conversion_efficiency)

    if_w = intermediate_focus_power(euv_w, collector_reflectivity,
                                    collection_solid_angle_sr)

    transmission = optical_train_transmission(mirror_count, mirror_reflectivity)
    wafer_w = if_w * transmission

    resolution = rayleigh_resolution(numerical_aperture, k1)
    dof = depth_of_focus(numerical_aperture)
    wph = throughput_wph(wafer_w, dose_mj_cm2)

    collector_eff = (if_w / euv_w * 100.0) if euv_w > 0 else 0.0

    stages = [
        {"label": "CO2 drive laser", "value": round(laser_power_kw, 2), "unit": "kW"},
        {"label": "Tin plasma (in-band EUV)", "value": round(euv_w, 1), "unit": "W"},
        {"label": "Intermediate focus", "value": round(if_w, 1), "unit": "W"},
        {"label": f"After {mirror_count} mirrors", "value": round(wafer_w, 3), "unit": "W"},
        {"label": "Printed half-pitch", "value": round(resolution, 2), "unit": "nm"},
        {"label": "Throughput", "value": round(wph, 1), "unit": "wafers/hr"},
    ]

    return SimulationResult(
        laser_power_kw=round(laser_power_kw, 3),
        conversion_efficiency_pct=round(conversion_efficiency * 100.0, 3),
        euv_generated_w=round(euv_w, 2),
        collector_efficiency_pct=round(collector_eff, 3),
        intermediate_focus_power_w=round(if_w, 2),
        mirror_count=mirror_count,
        mirror_reflectivity_pct=round(mirror_reflectivity * 100.0, 2),
        optical_transmission_pct=round(transmission * 100.0, 4),
        wafer_plane_power_w=round(wafer_w, 4),
        numerical_aperture=numerical_aperture,
        k1=k1,
        resolution_nm=round(resolution, 3),
        depth_of_focus_nm=round(dof, 2),
        resolution_target_met=bool(resolution <= target_resolution_nm),
        dose_mj_cm2=dose_mj_cm2,
        throughput_wph=round(wph, 2),
        stages=stages,
    )


def simulate_from_config(config: dict,
                         dose_mj_cm2: float = 30.0,
                         target_resolution_nm: float = 7.0) -> SimulationResult:
    """
    Adapter: take a chosen component configuration (as produced by
    optimizer.py) and pull the physics parameters out of it.

    Falls back to production-representative defaults for any category the
    configuration does not include, so the simulation never crashes mid-demo
    because a category was missing from the CSV.
    """
    specs = {}
    for component in config.get("components", []):
        specs.update(component.get("specs", {}))

    return run_simulation(
        laser_power_kw=specs.get("laser_power_kw", 20.0),
        conversion_efficiency=specs.get("conversion_efficiency", 0.05),
        collector_reflectivity=specs.get("collector_reflectivity", 0.55),
        collection_solid_angle_sr=specs.get("collection_solid_angle_sr", 5.0),
        mirror_count=int(specs.get("mirror_count", 10)),
        mirror_reflectivity=specs.get("mirror_reflectivity", 0.70),
        numerical_aperture=specs.get("numerical_aperture", 0.33),
        dose_mj_cm2=dose_mj_cm2,
        k1=specs.get("k1", DEFAULT_K1),
        target_resolution_nm=target_resolution_nm,
    )


if __name__ == "__main__":
    # Sanity run: representative NXE:3400B-class parameters.
    result = run_simulation(
        laser_power_kw=20.0,
        conversion_efficiency=0.05,
        collector_reflectivity=0.55,
        collection_solid_angle_sr=5.0,
        mirror_count=10,
        mirror_reflectivity=0.70,
        numerical_aperture=0.33,
    )
    for stage in result.stages:
        print(f"{stage['label']:<30} {stage['value']:>10} {stage['unit']}")
    print()
    print(f"Depth of focus : {result.depth_of_focus_nm} nm")
    print(f"7 nm target met: {result.resolution_target_met}")
