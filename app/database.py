import os

from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session

load_dotenv()


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Please add your Neon PostgreSQL connection string to .env."
        )

    url = make_url(database_url)

    # Use Psycopg 3 as the PostgreSQL driver.
    if url.drivername in ("postgresql", "postgres"):
        url = url.set(drivername="postgresql+psycopg")

    # Neon connections require SSL.
    if "sslmode" not in url.query:
        url = url.update_query_dict({"sslmode": "require"})

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=300,
    )


def get_db():
    with Session(get_engine()) as session:
        yield session