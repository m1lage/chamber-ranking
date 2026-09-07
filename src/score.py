"""Composite scoring for overseas Chinese chambers of commerce.

Design notes
------------
Four dimensions feed the composite score:

  reach      membership size, log-scaled
  activity   1/3/5 ordinal score for 2024 event programming
  position   2-5 ordinal score for the strategic value of the host city
  longevity  years since founding, log-scaled

Two decisions worth stating explicitly, because they drive the ranking:

1. Membership is log-scaled before normalising. The raw range spans 116 to
   110,000 members, so on a linear scale one chamber would dominate the
   dimension entirely and every other chamber would score near zero.

2. Missing values are not imputed. A chamber is scored on whatever
   dimensions it reports, and its weights are renormalised over those
   dimensions only. Coverage for each row is reported alongside the score so
   a reader can see how much evidence sits behind it. Annual dues are
   excluded from the composite for this reason: only 17 of 30 chambers
   report a figure, and dues measure a chamber's pricing model rather than
   its reach.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_WEIGHTS = {
    "reach": 0.40,
    "activity": 0.30,
    "position": 0.20,
    "longevity": 0.10,
}

REFERENCE_YEAR = 2025


def _minmax(series: pd.Series) -> pd.Series:
    """Scale to 0-1, ignoring NaN. A constant series maps to 0.5."""
    valid = series.dropna()
    if valid.empty:
        return series
    low, high = valid.min(), valid.max()
    if np.isclose(low, high):
        return series.where(series.isna(), 0.5)
    return (series - low) / (high - low)


def build_dimensions(df: pd.DataFrame) -> pd.DataFrame:
    """Turn parsed columns into four normalised 0-1 dimensions."""
    out = pd.DataFrame(index=df.index)

    out["reach"] = _minmax(np.log10(df["members"].where(df["members"] > 0)))
    out["activity"] = _minmax(df["activity_score"])
    out["position"] = _minmax(df["position_score"])

    age = REFERENCE_YEAR - df["founding_year"]
    out["longevity"] = _minmax(np.log10(age.where(age > 0)))

    return out


def composite(
    dims: pd.DataFrame,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Weighted mean over available dimensions, with coverage reported.

    Weights are renormalised per row across the dimensions that row actually
    has, so a chamber missing one input is not silently penalised for it.
    """
    weights = weights or DEFAULT_WEIGHTS
    missing = set(weights) - set(dims.columns)
    if missing:
        raise KeyError(f"weights reference unknown dimensions: {sorted(missing)}")

    w = pd.Series(weights, dtype=float)
    present = dims[w.index].notna()

    available_weight = present.mul(w, axis=1).sum(axis=1)
    weighted_sum = dims[w.index].fillna(0.0).mul(w, axis=1).sum(axis=1)

    score = np.where(
        available_weight > 0,
        weighted_sum / available_weight.replace(0, np.nan),
        np.nan,
    )

    return pd.DataFrame(
        {
            "score": np.round(pd.Series(score, index=dims.index) * 100, 1),
            "dimensions_present": present.sum(axis=1).astype(int),
            "weight_coverage": (available_weight / w.sum()).round(2),
        }
    )


def rank(df: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Full scoring pass: dimensions, composite, sorted ranking."""
    dims = build_dimensions(df)
    result = pd.concat([df, dims.round(3), composite(dims, weights)], axis=1)
    result = result.sort_values("score", ascending=False, na_position="last")
    result.insert(0, "rank", range(1, len(result) + 1))
    return result
