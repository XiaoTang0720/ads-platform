"""Synthetic ads data for ads-platform.

Creates 50 campaigns (10 AUTO, 40 MANUAL), 30 days of daily metrics, and plants
3 ROAS drops on MANUAL campaigns from day 20. The answer key is written to
anomalies.json, outside the database, so the agent cannot read it.

Run from the repo root (needs Postgres up and migrated):

    python -m data.synthetic.generate --seed 42            # first run
    python -m data.synthetic.generate --seed 42 --reset    # regenerate from scratch
"""

import argparse
import json
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from sqlalchemy import text

from app.db import get_engine

ANSWER_KEY = Path(__file__).with_name("anomalies.json")
START = date(2026, 10, 1)
ANOMALY_FROM_DAY = 20  # drops start on day 20 (1-based)
DROP_TYPES = ["conversion_collapse", "cpc_spike", "broad_match_traffic"]
MATCH_TYPES = ["BROAD", "PHRASE", "EXACT", "BROAD"]


def money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def simulate(rng: random.Random, days: int, drop: str | None):
    """Yield one metrics row (as a dict) per day for one ad + keyword pair."""
    impr_base = rng.randint(800, 4000)
    ctr = rng.uniform(0.008, 0.025)
    cpc = rng.uniform(0.5, 1.2)
    cvr = rng.uniform(0.05, 0.12)
    order_value = rng.uniform(25, 60)

    for d in range(days):
        day = START + timedelta(days=d)
        weekend = 0.8 if day.weekday() >= 5 else 1.0
        impressions = round(impr_base * weekend * rng.uniform(0.9, 1.1))
        clicks = round(impressions * ctr * rng.uniform(0.9, 1.1))
        price = cpc * rng.uniform(0.95, 1.05)
        conv = cvr
        billed_clicks = clicks

        if drop and d + 1 >= ANOMALY_FROM_DAY:
            if drop == "conversion_collapse":
                conv = cvr * 0.25  # 8% -> 2%: the page or stock is broken
            elif drop == "cpc_spike":
                price = price * 2.5  # competitor bidding war
            elif drop == "broad_match_traffic":
                # Junk searches: twice the clicks and impressions, same orders.
                impressions *= 2
                billed_clicks = clicks * 2

        orders = round(clicks * conv)  # orders come from the real clicks
        yield {
            "metric_date": day,
            "impressions": impressions,
            "clicks": billed_clicks,
            "spend": money(billed_clicks * price),
            "orders": orders,
            "sales": money(orders * order_value),
        }


UPSERT = text(
    """
    INSERT INTO daily_metrics (ad_id, keyword_id, metric_date, impressions, clicks, spend, orders, sales)
    VALUES (:ad_id, :keyword_id, :metric_date, :impressions, :clicks, :spend, :orders, :sales)
    ON CONFLICT ON CONSTRAINT uq_daily_metrics_ad_id_keyword_id_metric_date
    DO UPDATE SET impressions = EXCLUDED.impressions,
                  clicks      = EXCLUDED.clicks,
                  spend       = EXCLUDED.spend,
                  orders      = EXCLUDED.orders,
                  sales       = EXCLUDED.sales
    """
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--campaigns", type=int, default=50)
    parser.add_argument("--auto", type=int, default=10, help="how many campaigns are AUTO")
    parser.add_argument("--reset", action="store_true", help="delete all rows first (dev DB only)")
    args = parser.parse_args()

    rng = random.Random(args.seed)  # same seed -> same numbers every run
    auto = set(rng.sample(range(args.campaigns), args.auto))
    manual = [c for c in range(args.campaigns) if c not in auto]
    drops = {c: DROP_TYPES[k] for k, c in enumerate(rng.sample(manual, len(DROP_TYPES)))}

    engine = get_engine()
    with engine.begin() as conn:
        if args.reset:
            conn.execute(text(
                "TRUNCATE daily_metrics, keyword, ad, ad_group, campaign, advertiser "
                "RESTART IDENTITY CASCADE"
            ))
        elif conn.execute(text("SELECT count(*) FROM advertiser")).scalar():
            print("Data already exists. Use --reset to regenerate. Nothing changed.")
            return

        advertisers = [
            conn.execute(
                text("INSERT INTO advertiser (name) VALUES (:n) RETURNING id"),
                {"n": f"Synthetic advertiser {i + 1}"},
            ).scalar()
            for i in range(3)
        ]

        answer_key = []
        metric_rows = []
        for c in range(args.campaigns):
            is_auto = c in auto
            campaign_id = conn.execute(
                text(
                    "INSERT INTO campaign (advertiser_id, name, targeting_type, daily_budget) "
                    "VALUES (:a, :n, :t, :b) RETURNING id"
                ),
                {
                    "a": advertisers[c % 3],
                    "n": f"Campaign {c + 1:02d}",
                    "t": "AUTO" if is_auto else "MANUAL",
                    "b": money(rng.uniform(20, 200)),
                },
            ).scalar()
            if c in drops:
                answer_key.append({
                    "campaign_id": campaign_id,
                    "campaign_name": f"Campaign {c + 1:02d}",
                    "drop_type": drops[c],
                    "from_day": ANOMALY_FROM_DAY,
                    "start_date": str(START + timedelta(days=ANOMALY_FROM_DAY - 1)),
                })

            for g in range(2):  # two ad groups per campaign
                ad_group_id = conn.execute(
                    text(
                        "INSERT INTO ad_group (campaign_id, name, default_bid) "
                        "VALUES (:c, :n, :b) RETURNING id"
                    ),
                    {"c": campaign_id, "n": f"Group {g + 1}", "b": money(rng.uniform(0.3, 1.5))},
                ).scalar()

                keyword_ids: list[int | None] = [None]  # AUTO: no keywords, keyword_id NULL
                if not is_auto:
                    keyword_ids = [
                        conn.execute(
                            text(
                                "INSERT INTO keyword (ad_group_id, text, match_type) "
                                "VALUES (:g, :t, :m) RETURNING id"
                            ),
                            {"g": ad_group_id, "t": f"term {c + 1}-{g + 1}-{k + 1}",
                             "m": MATCH_TYPES[k]},
                        ).scalar()
                        for k in range(4)
                    ]

                for a in range(2):  # two ads per ad group
                    ad_id = conn.execute(
                        text("INSERT INTO ad (ad_group_id, asin) VALUES (:g, :s) RETURNING id"),
                        {"g": ad_group_id, "s": f"B0SYN{c:02d}{g}{a}0"},
                    ).scalar()
                    for kw in keyword_ids:
                        for row in simulate(rng, args.days, drops.get(c)):
                            metric_rows.append({"ad_id": ad_id, "keyword_id": kw, **row})

        # Insert in batches; the upsert makes a repeated batch harmless.
        for start in range(0, len(metric_rows), 2000):
            conn.execute(UPSERT, metric_rows[start:start + 2000])

    ANSWER_KEY.write_text(json.dumps(answer_key, indent=2))
    print(f"Inserted {len(metric_rows)} daily_metrics rows. Answer key: {ANSWER_KEY}")


if __name__ == "__main__":
    main()
