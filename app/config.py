import os

from dotenv import load_dotenv
from sqlalchemy.engine import URL

# Reads .env from the project root into os.environ. Real environment variables win.
load_dotenv()


def database_url() -> URL:
    """Build the Postgres connection URL from environment variables.

    Host defaults to 127.0.0.1 (the port docker-compose publishes). The password has no
    default: a missing one raises KeyError instead of silently connecting with a weak one.
    """
    return URL.create(
        drivername="postgresql+psycopg",  # SQLAlchemy dialect + the psycopg 3 driver
        username=os.environ.get("POSTGRES_USER", "ads"),
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ.get("POSTGRES_DB", "ads"),
    )
