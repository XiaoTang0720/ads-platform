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
