from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
target_metadata = Base.metadata

MANAGED_SEARCH_EXPRESSION_INDEXES = {
    "ix_genes_search_document",
    "ix_organisms_search_document",
    "ix_proteins_search_document",
}


def include_object(
    object: object, name: str | None, type_: str, reflected: bool, compare_to: object
) -> bool:
    # PostgreSQL deparses expression indexes with casts and parentheses that
    # Alembic cannot compare reliably to their source SQL. These three indexes
    # are owned by the reviewed 0002 migration and checked separately.
    return not (type_ == "index" and name in MANAGED_SEARCH_EXPRESSION_INDEXES)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
