import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parse import (  # noqa: E402
    membership_qualifier,
    parse_fee,
    parse_membership,
    parse_score,
    parse_year,
)


class TestMembership:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("11万", 110_000.0),
            (6000, 6000.0),
            ("5160", 5160.0),
            ("1200多人", 1260.0),
            ("800余", 840.0),
            ("超700", 770.0),
            ("近700", 665.0),
            ("超过500", 550.0),
            ("400以上", 440.0),
            ("少于500", 400.0),
            ("160多", 168.0),
        ],
    )
    def test_point_estimates(self, raw, expected):
        assert parse_membership(raw) == pytest.approx(expected, rel=1e-3)

    def test_longest_qualifier_wins(self):
        # "超过500" must not be read as the bare "超" rule applied twice.
        assert parse_membership("超过500") == parse_membership("超500")

    @pytest.mark.parametrize("raw", ["na", "", None, "  ", "-"])
    def test_missing(self, raw):
        assert parse_membership(raw) is None

    @pytest.mark.parametrize(
        "raw,direction",
        [("超700", "above"), ("少于500", "below"), ("近700", "below"),
         ("800余", "above"), (500, None)],
    )
    def test_qualifier_direction(self, raw, direction):
        assert membership_qualifier(raw) == direction


class TestFee:
    def test_numeric(self):
        assert parse_fee(1163) == 1163.0
        assert parse_fee(66.65) == pytest.approx(66.65)

    def test_annotated_zero_is_not_missing(self):
        # This chamber charges no dues; that is a real value, not a gap.
        assert parse_fee("（唯一一个）0") == 0.0

    @pytest.mark.parametrize("raw", ["na", "NA", None, ""])
    def test_missing(self, raw):
        assert parse_fee(raw) is None


class TestScoreAndYear:
    def test_score(self):
        assert parse_score(5) == 5.0
        assert parse_score("-") is None
        assert parse_score("na") is None

    def test_year(self):
        assert parse_year(1900) == 1900
        assert parse_year(2018.0) == 2018

    def test_year_out_of_range(self):
        assert parse_year(12) is None
        assert parse_year(3000) is None
