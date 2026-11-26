"""Tests for the synthetic data generator.

The simulation tests need no database. The row-count and rerun-guard tests use the
local database; they skip when it is down or empty (run the generator first).
"""

import random
import sys

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.config import database_url
from data.synthetic import generate

EXPECTED_COUNTS = {
    "advertiser": 3,
    "campaign": 50,
    "ad_group": 100,
    "ad": 200,
    "keyword": 320,
    "daily_metrics": 20400,
}


def test_same_seed_gives_same_rows():
    first = list(generate.simulate(random.Random(7), 30, "cpc_spike"))
    second = list(generate.simulate(random.Random(7), 30, "cpc_spike"))
    assert len(first) == 30
    assert first == second


def test_drop_changes_only_from_day_20():
    normal = list(generate.simulate(random.Random(7), 30, None))
    dropped = list(generate.simulate(random.Random(7), 30, "conversion_collapse"))
    assert normal[:19] == dropped[:19]  # days 1-19 are untouched
    assert normal[19:] != dropped[19:]  # days 20-30 differ


@pytest.fixture
def engine():
    try:
        eng = create_engine(database_url())
        with eng.connect() as conn:
            conn.execute(text("select 1"))
    except (KeyError, OperationalError) as exc:
        pytest.skip(f"database not reachable: {type(exc).__name__}")
    yield eng
    eng.dispose()


def _counts(engine):
    with engine.connect() as conn:
        return {
            table: conn.execute(text(f"select count(*) from {table}")).scalar()
            for table in EXPECTED_COUNTS
        }


def test_row_counts_match_the_plan(engine):
    counts = _counts(engine)
    if counts["advertiser"] == 0:
        pytest.skip("no synthetic data: run python -m data.synthetic.generate first")
    assert counts == EXPECTED_COUNTS


def test_rerun_without_reset_changes_nothing(engine, capsys, monkeypatch):
    before = _counts(engine)
    if before["advertiser"] == 0:
        pytest.skip("no synthetic data: run python -m data.synthetic.generate first")
    monkeypatch.setattr(sys, "argv", ["generate", "--seed", "42"])
    generate.main()
    assert "Nothing changed" in capsys.readouterr().out
    assert _counts(engine) == before
