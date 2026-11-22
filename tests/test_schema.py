"""Schema tests. They need the database up and migrated; otherwise they skip.

Each test runs inside a transaction that is rolled back at the end, so no data is left behind.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.config import database_url
from app.models import (
    Ad,
    AdGroup,
    Advertiser,
    Campaign,
    DailyMetrics,
    Keyword,
    MatchType,
    TargetingType,
)


@pytest.fixture
def session():
    engine = create_engine(database_url_or_skip())
    try:
        connection = engine.connect()
    except OperationalError as exc:
        engine.dispose()
        pytest.skip(f"database not reachable (docker compose up -d?): {type(exc).__name__}")
    # Begin first: inspect() or any query would auto-begin a transaction, and a second begin() fails.
    transaction = connection.begin()
    if not inspect(connection).has_table("daily_metrics"):
        transaction.rollback()
        connection.close()
        engine.dispose()
        pytest.skip("tables missing: run `alembic upgrade head` first")
    # create_savepoint: when a test hits an IntegrityError, only the savepoint rolls back,
    # not the outer transaction we use for cleanup.
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield db
    db.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


def database_url_or_skip():
    try:
        return database_url()
    except KeyError:
        pytest.skip("POSTGRES_PASSWORD is not set (create .env from .env.example)")


@pytest.fixture
def ad_with_keyword(session):
    advertiser = Advertiser(name="Acme")
    session.add(advertiser)
    session.flush()  # sends the INSERT now, so advertiser.id is filled in
    campaign = Campaign(
        advertiser_id=advertiser.id,
        name="Spring sale",
        targeting_type=TargetingType.MANUAL,
        daily_budget=Decimal("50.00"),
    )
    session.add(campaign)
    session.flush()
    ad_group = AdGroup(campaign_id=campaign.id, name="Shoes", default_bid=Decimal("0.75"))
    session.add(ad_group)
    session.flush()
    ad = Ad(ad_group_id=ad_group.id, asin="B000000001")
    keyword = Keyword(ad_group_id=ad_group.id, text="running shoes", match_type=MatchType.EXACT)
    session.add_all([ad, keyword])
    session.flush()
    return ad, keyword


def _metrics(ad, keyword, **overrides):
    values = dict(
        ad_id=ad.id,
        keyword_id=keyword.id if keyword else None,
        metric_date=date(2026, 11, 1),
        impressions=1000,
        clicks=20,
        spend=Decimal("12.50"),
        orders=2,
        sales=Decimal("60.00"),
    )
    values.update(overrides)
    return DailyMetrics(**values)


def test_hierarchy_and_defaults(session, ad_with_keyword):
    ad, keyword = ad_with_keyword
    session.add(_metrics(ad, keyword))
    session.flush()

    # Defaults come from the database: status = ENABLED, is_negative = false.
    assert session.get(Ad, ad.id).status.value == "ENABLED"
    assert session.get(Keyword, keyword.id).is_negative is False

    # CTR = clicks / impressions, computed in SQL.
    ctr = session.scalar(select(func.sum(DailyMetrics.clicks) * 1.0 / func.sum(DailyMetrics.impressions)))
    assert float(ctr) == pytest.approx(0.02)


def test_duplicate_metrics_row_is_rejected(session, ad_with_keyword):
    ad, keyword = ad_with_keyword
    session.add(_metrics(ad, keyword))
    session.flush()
    session.add(_metrics(ad, keyword))
    with pytest.raises(IntegrityError):
        session.flush()


def test_duplicate_metrics_row_without_keyword_is_rejected(session, ad_with_keyword):
    """AUTO targeting has no keyword (NULL). NULLS NOT DISTINCT must still block the duplicate."""
    ad, _ = ad_with_keyword
    session.add(_metrics(ad, None))
    session.flush()
    session.add(_metrics(ad, None))
    with pytest.raises(IntegrityError):
        session.flush()


def test_clicks_cannot_exceed_impressions(session, ad_with_keyword):
    ad, keyword = ad_with_keyword
    session.add(_metrics(ad, keyword, impressions=10, clicks=11))
    with pytest.raises(IntegrityError):
        session.flush()


def test_ad_with_history_cannot_be_deleted(session, ad_with_keyword):
    ad, keyword = ad_with_keyword
    session.add(_metrics(ad, keyword))
    session.flush()
    session.delete(ad)
    with pytest.raises(IntegrityError):
        session.flush()
