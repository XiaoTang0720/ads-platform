from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import database_url

# Fixed constraint names. Without them Postgres invents names, and a later migration
# cannot refer to a constraint it did not name.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Every model inherits from this. Base.metadata is the list of all tables."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def get_engine():
    """Create an engine (a connection pool). Called when needed, so importing never connects."""
    return create_engine(database_url())


def get_sessionmaker():
    return sessionmaker(bind=get_engine())
