"""Parsing helpers for the raw chamber-of-commerce workbook.

The source data was compiled by hand, so numeric fields arrive as free text:
membership counts appear as "11万", "3000多", "超700", "少于500" and similar,
and annual dues carry "na" placeholders plus one annotated zero.

Each parser returns a float or None. None means "not reported" and is kept
distinct from a genuine zero throughout the pipeline.
"""

from __future__ import annotations

import re
from typing import Optional

# Chinese magnitude suffixes.
MAGNITUDES = {
    "万": 10_000,
    "千": 1_000,
    "百": 100,
}

# Qualifiers that modify a stated figure. The multiplier encodes how the
# reported number should be read: "超700" means more than 700, "少于500"
# means fewer than 500. We nudge the point estimate accordingly rather than
# discarding the qualifier, and record its direction for auditing.
QUALIFIERS = {
    "超过": ("above", 1.10),
    "超": ("above", 1.10),
    "多于": ("above", 1.10),
    "以上": ("above", 1.10),
    "余": ("above", 1.05),
    "多": ("above", 1.05),
    "近": ("below", 0.95),
    "少于": ("below", 0.80),
    "约": ("approx", 1.00),
}

# Longest first so "超过" is matched before "超" and "多于" before "多".
_QUALIFIER_KEYS = sorted(QUALIFIERS, key=len, reverse=True)

_NUMERIC = re.compile(r"\d+(?:\.\d+)?")


def _is_blank(value) -> bool:
    if value is None:
        return True
    text = str(value).strip().lower()
    return text in {"", "na", "n/a", "nan", "none", "-", "—"}


def parse_membership(value) -> Optional[float]:
    """Parse a membership count into a float point estimate.

    >>> parse_membership("11万")
    110000.0
    >>> parse_membership("3000多")
    3150.0
    >>> parse_membership("少于500")
    400.0
    >>> parse_membership(5160)
    5160.0
    >>> parse_membership("na") is None
    True
    """
    if _is_blank(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    text = text.replace("人", "").replace(",", "").replace("，", "")

    match = _NUMERIC.search(text)
    if not match:
        return None
    number = float(match.group())

    for suffix, factor in MAGNITUDES.items():
        if suffix in text:
            number *= factor
            break

    for key in _QUALIFIER_KEYS:
        if key in text:
            number *= QUALIFIERS[key][1]
            break

    return round(number, 1)


def membership_qualifier(value) -> Optional[str]:
    """Return 'above', 'below', 'approx' or None for a membership string.

    Kept separate from the point estimate so the ranking can flag which
    figures are bounds rather than exact counts.
    """
    if _is_blank(value) or isinstance(value, (int, float)):
        return None
    text = str(value)
    for key in _QUALIFIER_KEYS:
        if key in text:
            return QUALIFIERS[key][0]
    return None


def parse_fee(value) -> Optional[float]:
    """Parse annual dues into a float.

    Blank placeholders return None. One row reads '（唯一一個）0' — an
    annotated zero meaning the chamber charges no dues — which parses to 0.0
    and is deliberately NOT treated as missing.

    >>> parse_fee(1163)
    1163.0
    >>> parse_fee("na") is None
    True
    >>> parse_fee("（唯一一个）0")
    0.0
    """
    if _is_blank(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    match = _NUMERIC.search(str(value))
    return float(match.group()) if match else None


def parse_score(value) -> Optional[float]:
    """Parse an ordinal score column, treating '-' as not scored."""
    if _is_blank(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_year(value) -> Optional[int]:
    if _is_blank(value):
        return None
    try:
        year = int(float(value))
    except (TypeError, ValueError):
        return None
    return year if 1800 <= year <= 2030 else None
