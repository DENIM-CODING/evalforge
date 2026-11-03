import os

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url
from dotenv import load_dotenv

from app.database import Base
from app import models  # noqa: F401


load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError(
        "DATABASE_URL is not configured in the environment."
    )

url = make_url(database_url)

if url.drivername in ("postgresql", "postgres"):
    url = url.set(drivername="postgresql+psycopg")

if "sslmode" not in url.query:
    url = url.update_query_dict({"sslmode": "require"})

config.set_main_option(
    "sqlalchemy.url",
    url.render_as_string(hide_password=False).replace("%", "%%"),
)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()