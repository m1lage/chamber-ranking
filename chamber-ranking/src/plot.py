"""Generate the two figures in output/.

    python src/plot.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.font_manager
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

# Noto Sans CJK renders the chamber names; fall back silently if absent.
for candidate in ("Noto Sans CJK JP", "WenQuanYi Zen Hei", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(candidate, fallback_to_default=False)
        plt.rcParams["font.family"] = candidate
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

DIMS = ["reach", "activity", "position", "longevity"]
WEIGHTS = {"reach": 0.40, "activity": 0.30, "position": 0.20, "longevity": 0.10}
COLORS = ["#2E5E8A", "#4E9A6B", "#C4913C", "#8A5A83"]


def contribution_chart(ranked: pd.DataFrame, top: int = 12) -> None:
    d = ranked.head(top).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6))

    left = pd.Series(0.0, index=d.index)
    for dim, color in zip(DIMS, COLORS):
        # Contribution on the same renormalised basis as the composite score.
        contrib = (d[dim].fillna(0) * WEIGHTS[dim] / d["weight_coverage"]) * 100
        ax.barh(d["chamber"], contrib, left=left, color=color, label=dim, height=0.7)
        left += contrib

    ax.set_xlabel("Composite score (0-100), by weighted dimension")
    ax.set_title(f"Top {top} chambers — what drives each score", pad=12, loc="left")
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.14), fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "score_composition.png", dpi=150)
    plt.close(fig)


def coverage_chart(coverage: pd.DataFrame) -> None:
    d = coverage.sort_values("coverage")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    colors = ["#B03A3A" if c < 0.7 else "#2E5E8A" for c in d["coverage"]]
    ax.barh(d["field"], d["coverage"] * 100, color=colors, height=0.6)
    for y, (cov, rep, tot) in enumerate(zip(d["coverage"], d["reported"], d["total"])):
        ax.text(cov * 100 + 1.5, y, f"{rep}/{tot}", va="center", fontsize=9)
    ax.set_xlim(0, 112)
    ax.set_xlabel("% of chambers reporting the field")
    ax.set_title("Data coverage — red fields fall below 70%", pad=10, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "coverage.png", dpi=150)
    plt.close(fig)


def main() -> None:
    ranked = pd.read_csv(OUT / "ranking.csv")
    coverage = pd.read_csv(OUT / "coverage.csv")
    contribution_chart(ranked)
    coverage_chart(coverage)
    print(f"Wrote {OUT/'score_composition.png'} and {OUT/'coverage.png'}")


if __name__ == "__main__":
    main()
