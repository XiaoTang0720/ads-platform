"""Ad data model: Advertiser > Campaign > Ad Group > Ad / Keyword, plus Daily Metrics.

Mirrors the Amazon Sponsored Products hierarchy. Each class is one table.
"""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import text as sql_text  # the Keyword.text column below would hide a bare `text`
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TargetingType(str, enum.Enum):
    AUTO = "AUTO"  # Amazon picks the matches
    MANUAL = "MANUAL"  # the advertiser picks keywords


class Status(str, enum.Enum):
    ENABLED = "ENABLED"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"  # "deleted" for the advertiser, but history is kept


class MatchType(str, enum.Enum):
    BROAD = "BROAD"
    PHRASE = "PHRASE"
    EXACT = "EXACT"


def _enum(py_enum: type[enum.Enum], name: str) -> Enum:
    """Store an enum as VARCHAR plus a CHECK constraint (easier to change than a Postgres ENUM type)."""
    return Enum(py_enum, name=name, native_enum=False, length=16, create_constraint=True)


# Money: NUMERIC(12,2) is exact decimal. float would give 0.1 + 0.2 = 0.30000000000000004.
# Counts: BIGINT, because impressions can pass 2 billion (the INTEGER limit).
Money = Numeric(12, 2)


class Advertiser(Base):
    __tablename__ = "advertiser"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Campaign(Base):
    __tablename__ = "campaign"
    __table_args__ = (CheckConstraint("daily_budget >= 0", name="daily_budget_non_negative"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    advertiser_id: Mapped[int] = mapped_column(
        ForeignKey("advertiser.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    targeting_type: Mapped[TargetingType] = mapped_column(_enum(TargetingType, "targeting_type"))
    daily_budget: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[Status] = mapped_column(_enum(Status, "status"), server_default="ENABLED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdGroup(Base):
    __tablename__ = "ad_group"
    __table_args__ = (CheckConstraint("default_bid >= 0", name="default_bid_non_negative"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaign.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    default_bid: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[Status] = mapped_column(_enum(Status, "status"), server_default="ENABLED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Ad(Base):
    __tablename__ = "ad"
    # The same product (ASIN) can appear only once per ad group. This unique index also serves
    # "all ads of an ad group" queries, because ad_group_id is its first column.
    __table_args__ = (UniqueConstraint("ad_group_id", "asin"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ad_group_id: Mapped[int] = mapped_column(ForeignKey("ad_group.id", ondelete="CASCADE"))
    asin: Mapped[str] = mapped_column(String(10))  # Amazon product id, 10 characters
    status: Mapped[Status] = mapped_column(_enum(Status, "status"), server_default="ENABLED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Keyword(Base):
    __tablename__ = "keyword"
    __table_args__ = (
        UniqueConstraint("ad_group_id", "text", "match_type"),
        CheckConstraint("bid >= 0", name="bid_non_negative"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ad_group_id: Mapped[int] = mapped_column(ForeignKey("ad_group.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(String(200))
    match_type: Mapped[MatchType] = mapped_column(_enum(MatchType, "match_type"))
    # A negative keyword blocks a search term, so it is never bid on.
    is_negative: Mapped[bool] = mapped_column(Boolean, server_default=sql_text("false"))
    # NULL means "use the ad group's default_bid".
    bid: Mapped[Decimal | None] = mapped_column(Money)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyMetrics(Base):
    """Fact table: one row per ad, per keyword, per day. Grows every day."""

    __tablename__ = "daily_metrics"
    __table_args__ = (
        # Makes reruns safe (idempotent). NULLS NOT DISTINCT matters: an ad on AUTO targeting
        # has keyword_id = NULL, and plain Postgres treats two NULLs as different, so
        # duplicates would slip through. Needs Postgres 15 or newer.
        # ad_id is first, so "one ad over a date range" uses this unique index.
        UniqueConstraint(
            "ad_id", "keyword_id", "metric_date", postgresql_nulls_not_distinct=True
        ),
        CheckConstraint("clicks <= impressions", name="clicks_lte_impressions"),
        CheckConstraint(
            "impressions >= 0 AND clicks >= 0 AND orders >= 0 AND spend >= 0 AND sales >= 0",
            name="non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # RESTRICT (not CASCADE): you cannot delete an ad that has history. Archive it instead.
    ad_id: Mapped[int] = mapped_column(ForeignKey("ad.id", ondelete="RESTRICT"))
    keyword_id: Mapped[int | None] = mapped_column(
        ForeignKey("keyword.id", ondelete="RESTRICT"), index=True
    )
    metric_date: Mapped[date] = mapped_column(Date)
    impressions: Mapped[int] = mapped_column(BigInteger, server_default=sql_text("0"))
    clicks: Mapped[int] = mapped_column(BigInteger, server_default=sql_text("0"))
    spend: Mapped[Decimal] = mapped_column(Money, server_default=sql_text("0"))
    orders: Mapped[int] = mapped_column(BigInteger, server_default=sql_text("0"))
    sales: Mapped[Decimal] = mapped_column(Money, server_default=sql_text("0"))
