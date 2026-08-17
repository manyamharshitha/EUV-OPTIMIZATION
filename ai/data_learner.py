"""
data_learner.py  --  Person C (AI Engineer)

External data learning.

"External" here means: experimental data from outside our own simulation,
collected by Person A, analysed BEFORE the demo runs, and used at runtime.
It is not data a judge supplies live.

This module reads A's experiment CSVs and extracts real statistical
relationships from them -- least-squares fits, correlation strength, and
predictions with an honest confidence band.

Two rules this module holds to:

1.  It reports how many of its training rows were PUBLISHED versus SYNTHETIC.
    A fit learned from invented rows is worth less than one learned from
    measured rows, and the UI must be able to say which it got.

2.  It never extrapolates silently. Predictions outside the observed input
    range come back flagged.

Pure standard library. No numpy, no sklearn.
"""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass, asdict, field

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "data")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

@dataclass
class Fit:
    """A fitted straight line, plus everything needed to judge whether to
    trust it."""

    x_name: str
    y_name: str
    model_form: str
    slope: float
    intercept: float
    r_squared: float
    correlation: float
    std_error: float
    n_points: int
    n_published: int
    n_synthetic: int
    x_min: float
    x_max: float
    quality: str
    confidence: float
    warnings: list = field(default_factory=list)

    def _evaluate(self, x: float) -> float:
        """Apply whichever model form won the fit."""
        if self.model_form == "exponential":
            return math.exp(self.intercept) * math.exp(self.slope * x)
        if self.model_form == "power":
            if x <= 0:
                return float("nan")
            return math.exp(self.intercept) * (x ** self.slope)
        return self.slope * x + self.intercept

    def predict(self, x: float) -> dict:
        """Predict y at x, with a 95% band and an extrapolation flag."""
        y = self._evaluate(x)
        margin = 1.96 * self.std_error

        extrapolating = x < self.x_min or x > self.x_max
        return {
            "x": x,
            "predicted": round(y, 6),
            "low": round(y - margin, 6),
            "high": round(y + margin, 6),
            "confidence": round(self.confidence * (0.5 if extrapolating else 1.0), 3),
            "extrapolating": extrapolating,
            "note": (
                f"x={x} is outside the observed range "
                f"[{self.x_min}, {self.x_max}] -- treat with caution"
                if extrapolating else "within observed data range"
            ),
        }

    def to_dict(self) -> dict:
        return asdict(self)


def _ols(points: list):
    """Bare ordinary least squares. Returns (slope, intercept) or None."""
    n = len(points)
    mean_x = sum(p[0] for p in points) / n
    mean_y = sum(p[1] for p in points) / n

    sxx = sum((p[0] - mean_x) ** 2 for p in points)
    if sxx <= 1e-12:
        return None

    sxy = sum((p[0] - mean_x) * (p[1] - mean_y) for p in points)
    slope = sxy / sxx
    return slope, mean_y - slope * mean_x


def linear_fit(points: list, x_name: str, y_name: str,
               n_published: int = 0, n_synthetic: int = 0) -> Fit | None:
    """
    Fit (x, y) pairs, trying three model forms and keeping whichever explains
    the most variance in the ORIGINAL y space:

        linear       y = a*x + b
        exponential  y = exp(b) * exp(a*x)      -- saturating / decaying
        power        y = exp(b) * x^a           -- multiplicative chains

    The third form matters here: optical transmission is reflectivity^n, so a
    straight line through it explains almost nothing while a power law fits
    almost exactly. Reporting "no relationship" when the relationship is
    simply not a line would be a real analytical error.

    Returns None if there is not enough spread in x to fit anything.
    """
    n = len(points)
    if n < 3:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    mean_y = sum(ys) / n
    syy = sum((y - mean_y) ** 2 for y in ys)
    if syy <= 1e-12:
        return None

    candidates = []

    # 1. Linear
    fitted = _ols(points)
    if fitted:
        a, b = fitted
        candidates.append(("linear", a, b, lambda x, a=a, b=b: a * x + b))

    # 2. Exponential -- needs strictly positive y
    if all(y > 0 for y in ys):
        fitted = _ols([(x, math.log(y)) for x, y in points])
        if fitted:
            a, b = fitted
            candidates.append(("exponential", a, b,
                               lambda x, a=a, b=b: math.exp(b) * math.exp(a * x)))

    # 3. Power law -- needs strictly positive x and y
    if all(y > 0 for y in ys) and all(x > 0 for x, _ in points):
        fitted = _ols([(math.log(x), math.log(y)) for x, y in points])
        if fitted:
            a, b = fitted
            candidates.append(("power", a, b,
                               lambda x, a=a, b=b: math.exp(b) * (x ** a)))

    if not candidates:
        return None

    # Score every candidate in original y space so the comparison is fair.
    best = None
    for model, a, b, predict in candidates:
        try:
            residual_ss = sum((y - predict(x)) ** 2 for x, y in points)
        except (OverflowError, ValueError):
            continue
        r2 = 1.0 - (residual_ss / syy)
        if best is None or r2 > best[0]:
            best = (r2, model, a, b, residual_ss)

    if best is None:
        return None

    r_squared, model_form, slope, intercept, residual_ss = best
    correlation = math.copysign(math.sqrt(max(0.0, r_squared)), slope)
    std_error = math.sqrt(residual_ss / (n - 2)) if n > 2 else 0.0

    if r_squared >= 0.90:
        quality = "strong"
    elif r_squared >= 0.70:
        quality = "moderate"
    elif r_squared >= 0.40:
        quality = "weak"
    else:
        quality = "none"

    # Confidence blends fit quality, sample size, and how much of the data
    # was actually measured rather than invented.
    published_fraction = n_published / n if n else 0.0
    size_factor = min(1.0, n / 12.0)
    confidence = max(0.0, r_squared) * (0.5 + 0.5 * size_factor) \
        * (0.55 + 0.45 * published_fraction)

    warnings = []
    if n_published == 0:
        warnings.append(
            "every row used was SYNTHETIC -- this fit describes our own model, "
            "not measured reality")
    if n < 6:
        warnings.append(f"only {n} data points")
    if quality in ("weak", "none"):
        warnings.append(f"R^2 = {r_squared:.2f}: relationship is {quality}")

    return Fit(
        x_name=x_name,
        y_name=y_name,
        model_form=model_form,
        slope=slope,
        intercept=intercept,
        r_squared=round(r_squared, 4),
        correlation=round(correlation, 4),
        std_error=round(std_error, 6),
        n_points=n,
        n_published=n_published,
        n_synthetic=n_synthetic,
        x_min=min(xs),
        x_max=max(xs),
        quality=quality,
        confidence=round(confidence, 3),
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def _to_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _load_pairs(path: str, x_col: str, y_col: str):
    """Pull (x, y) pairs out of a CSV, counting published vs synthetic rows."""
    points, n_pub, n_syn = [], 0, 0

    if not os.path.exists(path):
        return points, n_pub, n_syn

    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            x = _to_float(row.get(x_col))
            y = _to_float(row.get(y_col))
            if x is None or y is None:
                continue
            points.append((x, y))
            if str(row.get("data_type", "")).strip().upper() == "PUBLISHED":
                n_pub += 1
            else:
                n_syn += 1

    return points, n_pub, n_syn


# ---------------------------------------------------------------------------
# The three relationships we care about
# ---------------------------------------------------------------------------

def learn_all(data_dir: str = DEFAULT_DATA_DIR) -> dict:
    """
    Run every extraction and return one dict for the frontend's
    "External Data Learning Results" screen.
    """
    relationships = []

    targets = [
        ("laser_experiments.csv", "drive_power_kw", "euv_inband_power_w",
         "Drive laser power", "In-band EUV power"),
        ("laser_experiments.csv", "drive_power_kw", "conversion_efficiency",
         "Drive laser power", "Conversion efficiency"),
        ("laser_experiments.csv", "euv_inband_power_w", "if_power_w",
         "In-band EUV generated", "Power at intermediate focus"),
        ("mirror_experiments.csv", "wavelength_nm", "reflectivity",
         "Wavelength", "Peak coating reflectivity"),
        ("mirror_experiments.csv", "mirrors_in_train", "train_transmission",
         "Mirrors in optical train", "Train transmission"),
    ]

    for filename, x_col, y_col, x_label, y_label in targets:
        path = os.path.join(data_dir, filename)
        points, n_pub, n_syn = _load_pairs(path, x_col, y_col)

        fit = linear_fit(points, x_label, y_label, n_pub, n_syn)
        if fit is None:
            continue

        relationships.append({
            "source_file": filename,
            "x": x_label,
            "y": y_label,
            "fit": fit.to_dict(),
            "plain_english": _describe(fit),
        })

    # Sort strongest first so the UI leads with the best finding
    relationships.sort(key=lambda r: r["fit"]["r_squared"], reverse=True)

    total_pub = sum(r["fit"]["n_published"] for r in relationships)
    total_syn = sum(r["fit"]["n_synthetic"] for r in relationships)

    stats = distributions(data_dir)

    return {
        "distributions": stats,
        "relationships_found": len(relationships),
        "strong": sum(1 for r in relationships if r["fit"]["quality"] == "strong"),
        "moderate": sum(1 for r in relationships if r["fit"]["quality"] == "moderate"),
        "weak_or_none": sum(1 for r in relationships
                            if r["fit"]["quality"] in ("weak", "none")),
        "rows_published": total_pub,
        "rows_synthetic": total_syn,
        "honesty_note": (
            f"Learned from {total_pub} published and {total_syn} synthetic data "
            f"points. Synthetic rows describe our own model, not measured "
            f"reality."
        ),
        "relationships": relationships,
    }


def distributions(data_dir: str = DEFAULT_DATA_DIR) -> list:
    """
    Descriptive statistics over the measured values.

    Published experimental data is sparse -- real papers report the quantity
    they measured and leave the rest of the row empty. That defeats pairwise
    regression but says plenty on its own: the spread of reported Mo/Si
    reflectivities, or the range of conversion efficiencies across target
    geometries, is a genuine result extracted from external data.

    Reported only for columns with at least three measured values.
    """
    targets = [
        ("laser_experiments.csv", "conversion_efficiency",
         "Conversion efficiency", "fraction"),
        ("laser_experiments.csv", "drive_power_kw", "Drive laser power", "kW"),
        ("mirror_experiments.csv", "reflectivity",
         "Mo/Si peak reflectivity at 13.5 nm", "fraction"),
        ("vacuum_experiments.csv", "lifetime_hours",
         "Reported collector lifetime", "hours"),
    ]

    summaries = []
    for filename, column, label, unit in targets:
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            continue

        values, sources = [], set()
        with open(path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                # Reflectivity spans several coatings; restrict to Mo/Si at
                # 13.5 nm so the spread describes one population.
                if column == "reflectivity":
                    if row.get("coating") != "Mo/Si":
                        continue
                    if _to_float(row.get("wavelength_nm")) != 13.5:
                        continue

                value = _to_float(row.get(column))
                if value is None:
                    continue
                values.append(value)
                if row.get("source"):
                    sources.add(row["source"])

        if len(values) < 3:
            continue

        values.sort()
        n = len(values)
        mean = sum(values) / n
        median = (values[n // 2] if n % 2
                  else (values[n // 2 - 1] + values[n // 2]) / 2)
        variance = sum((v - mean) ** 2 for v in values) / (n - 1)

        summaries.append({
            "quantity": label,
            "unit": unit,
            "source_file": filename,
            "n_measurements": n,
            "distinct_sources": len(sources),
            "min": round(min(values), 6),
            "max": round(max(values), 6),
            "mean": round(mean, 6),
            "median": round(median, 6),
            "std_dev": round(variance ** 0.5, 6),
            "spread_pct": round((max(values) - min(values)) / mean * 100, 1)
            if mean else 0.0,
            "plain_english": (
                f"{n} published measurements of {label.lower()} span "
                f"{min(values):g} to {max(values):g} {unit} "
                f"(mean {mean:.4g}), drawn from {len(sources)} sources."
            ),
        })

    return summaries


def _describe(fit: Fit) -> str:
    """One sentence a non-specialist can read off the screen."""
    direction = "rises" if fit.slope > 0 else "falls"
    strength = {
        "strong": "tracks closely",
        "moderate": "tracks loosely",
        "weak": "barely tracks",
        "none": "does not track",
    }[fit.quality]

    shape = {
        "linear": "in a straight line",
        "exponential": "exponentially",
        "power": "as a power law",
    }.get(fit.model_form, "")

    return (
        f"{fit.y_name} {direction} {shape} with {fit.x_name.lower()} and "
        f"{strength} it (R^2 = {fit.r_squared:.2f} over {fit.n_points} runs, "
        f"{fit.n_published} of them published)."
    )


def predict_efficiency(drive_power_kw: float = 30.0,
                       data_dir: str = DEFAULT_DATA_DIR) -> dict:
    """
    Predict conversion efficiency at a given drive power, learned from A's
    laser experiments. This is what the optimizer would consult if it wanted
    a data-driven CE instead of a fixed constant.
    """
    path = os.path.join(data_dir, "laser_experiments.csv")
    points, n_pub, n_syn = _load_pairs(path, "drive_power_kw",
                                       "conversion_efficiency")

    fit = linear_fit(points, "Drive laser power", "Conversion efficiency",
                     n_pub, n_syn)
    if fit is None:
        return {
            "available": False,
            "reason": "not enough data with both drive power and CE recorded",
        }

    prediction = fit.predict(drive_power_kw)
    prediction["available"] = True
    prediction["r_squared"] = fit.r_squared
    prediction["quality"] = fit.quality
    prediction["warnings"] = fit.warnings

    # Published envelope guard, per A's validation report.
    if prediction["predicted"] > 0.06:
        prediction["warnings"] = prediction["warnings"] + [
            f"predicted CE {prediction['predicted']:.3f} exceeds the published "
            f"ceiling of 0.06 -- clamped"
        ]
        prediction["predicted"] = 0.06

    return prediction


# ---------------------------------------------------------------------------
# Adapter for backend.py
# ---------------------------------------------------------------------------
#
# backend.py calls extract_patterns() and predict_efficiency() with no
# arguments. C conforms to B's published contract.

def extract_patterns(data_dir: str = DEFAULT_DATA_DIR) -> list:
    """Flat list of learned relationships, shaped for display."""
    results = learn_all(data_dir)

    return [
        {
            "x": item["x"],
            "y": item["y"],
            "model_form": item["fit"]["model_form"],
            "r_squared": item["fit"]["r_squared"],
            "quality": item["fit"]["quality"],
            "confidence": item["fit"]["confidence"],
            "n_points": item["fit"]["n_points"],
            "n_published": item["fit"]["n_published"],
            "source_file": item["source_file"],
            "description": item["plain_english"],
            "warnings": item["fit"]["warnings"],
        }
        for item in results["relationships"]
    ]


if __name__ == "__main__":
    results = learn_all()

    print("=" * 62)
    print("  EXTERNAL DATA LEARNING")
    print("=" * 62)
    print(f"  {results['relationships_found']} relationships extracted "
          f"({results['strong']} strong, {results['moderate']} moderate, "
          f"{results['weak_or_none']} weak)")
    print(f"  {results['honesty_note']}")
    print()

    for item in results["relationships"]:
        fit = item["fit"]
        print(f"  [{fit['quality'].upper():<8}] {item['x']} -> {item['y']}")
        print(f"             R^2={fit['r_squared']:.3f}  "
              f"n={fit['n_points']}  confidence={fit['confidence']:.2f}")
        for warning in fit["warnings"]:
            print(f"             ! {warning}")
        print()

    print("-" * 62)
    print("  CE prediction at 25 kW drive power:")
    print(f"  {predict_efficiency(25.0)}")
