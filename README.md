# ads-platform

A small ads platform I am building to learn ad systems end to end: campaigns, ad serving, click/impression tracking, and reporting. Built with Python and FastAPI.

## Data model

```
advertiser 1--N campaign 1--N ad_group 1--N ad
                                     \--N keyword
daily_metrics: one row per ad x keyword x day (keyword can be NULL for AUTO targeting)
```

Models are in `app/models.py`. Migrations are in `migrations/versions/`.

## Run locally

Needs Docker (Colima on a Mac) and a `.env` file (copy `.env.example`, set `POSTGRES_PASSWORD`).

```
colima start
docker compose up -d            # or: docker-compose up -d
source .venv/bin/activate
alembic upgrade head            # creates the tables
python -m pytest -v             # schema tests skip if the database is down
uvicorn app.main:app --reload --host 127.0.0.1
```

The database listens on `127.0.0.1:5432` only.

## Synthetic data

`data/synthetic/generate.py` fills the tables with fake ads data: 50 campaigns, 30 days of metrics, and 3 planted ROAS drops from day 20. It is deterministic for a given seed.

```
python -m data.synthetic.generate --seed 42            # first run
python -m data.synthetic.generate --seed 42 --reset    # start over (dev DB only)
```

Without `--reset`, the script stops if data already exists. The answer key is written to `data/synthetic/anomalies.json`, which git ignores.

Find the drops:

```
docker exec -i ads-platform-db-1 psql -U ads < sql/roas_drops.sql
docker exec -i ads-platform-db-1 psql -U ads < sql/drop_causes.sql
```

Tests: `python -m pytest tests/test_synthetic.py -v`
