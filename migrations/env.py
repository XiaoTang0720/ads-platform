from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  (importing it registers every table on Base.metadata)
from app.config import database_url
from app.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# What the models say the database should look like. Autogenerate diffs this against the real DB.
target_metadata = Base.metadata


def _url() -> str:
    # `alembic -x url=...` overrides the URL (used to autogenerate against an empty scratch DB).
    override = context.get_x_argument(as_dictionary=True).get("url")
    return override or database_url().render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    """Print the SQL instead of running it: `alembic upgrade head --sql`."""
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and run the migrations."""
    connectable = create_engine(_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
