"""Run the full pipeline: load -> parse -> score -> write outputs.

    python src/run.py
    python src/run.py --weights reach=0.5,activity=0.3,position=0.2
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from parse import (
    membership_qualifier,
    parse_fee,
    parse_membership,
    parse_score,
    parse_year,
)
from score import DEFAULT_WEIGHTS, rank

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "chambers_30.xlsx"
OUT = ROOT / "output"

COLUMN_MAP = {
    "商会名称": "chamber",
    "会费 usd per year": "annual_dues_usd",
    "来源": "source",
    "地区": "region",
    "所属滴": "city",
    "founding date": "founding_year",
    "president": "president",
    "honors": "president_honors",
    "members": "members",
    "distinctive enterprise": "notable_members",
    "网址": "url",
    "24年重大项目名称": "flagship_2024",
    "活动得分": "activity_score",
    "地理位置得分": "position_score",
}


def load(path: Path = RAW) -> pd.DataFrame:
    raw = pd.read_excel(path)
    raw = raw[raw["商会名称"].notna()].copy()
    df = raw.rename(columns=COLUMN_MAP)

    df["members_raw"] = df["members"]
    df["members"] = df["members_raw"].map(parse_membership)
    df["members_bound"] = df["members_raw"].map(membership_qualifier)
    df["annual_dues_usd"] = df["annual_dues_usd"].map(parse_fee)
    df["activity_score"] = df["activity_score"].map(parse_score)
    df["position_score"] = df["position_score"].map(parse_score)
    df["founding_year"] = df["founding_year"].map(parse_year)

    return df.reset_index(drop=True)


def coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    fields = [
        "members",
        "activity_score",
        "position_score",
        "founding_year",
        "annual_dues_usd",
        "notable_members",
    ]
    return pd.DataFrame(
        {
            "field": fields,
            "reported": [int(df[f].notna().sum()) for f in fields],
            "total": len(df),
            "coverage": [round(df[f].notna().mean(), 2) for f in fields],
        }
    )


def parse_weights(text: str | None) -> dict[str, float] | None:
    if not text:
        return None
    weights = {}
    for pair in text.split(","):
        key, _, value = pair.partition("=")
        weights[key.strip()] = float(value)
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weights", help="e.g. reach=0.4,activity=0.3,position=0.2,longevity=0.1")
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    weights = parse_weights(args.weights) or DEFAULT_WEIGHTS

    df = load()
    ranked = rank(df, weights)

    OUT.mkdir(exist_ok=True)

    columns = [
        "rank", "chamber", "city", "region", "members", "members_bound",
        "activity_score", "position_score", "founding_year",
        "reach", "activity", "position", "longevity",
        "score", "dimensions_present", "weight_coverage",
    ]
    ranked[columns].to_csv(OUT / "ranking.csv", index=False)
    coverage_report(df).to_csv(OUT / "coverage.csv", index=False)

    print(f"Weights: {weights}\n")
    print(f"Top {args.top} of {len(ranked)} chambers\n")
    display = ranked.head(args.top)[
        ["rank", "chamber", "city", "members", "score", "weight_coverage"]
    ]
    print(display.to_string(index=False))
    print("\nField coverage")
    print(coverage_report(df).to_string(index=False))
    print(f"\nWrote {OUT / 'ranking.csv'} and {OUT / 'coverage.csv'}")


if __name__ == "__main__":
    main()
