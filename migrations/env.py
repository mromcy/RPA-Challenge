from contextlib import closing
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from resources.settings import get_settings

from resources.models import table_registry

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
config.set_main_option('sqlalchemy.url',get_settings().DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = table_registry.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def create_schemas_if_not_exists(engine, schema_name:str) ->None:
    # `closing` shuts each resource down even when the next line fails. Before,
    # the cursor was created inside the try and closed in the finally: if
    # `.cursor()` blew up - a connection invalidated in the pool, say - the
    # finally ran with a name that never existed, and the NameError replaced the
    # real error while still leaving the connection open.
    with (
        closing(engine.raw_connection()) as raw_connection,
        closing(raw_connection.cursor()) as cursor,
    ):
        cursor.execute(f'CREATE SCHEMA IF NOT EXISTS {schema_name}')
        raw_connection.commit()
    print(f'Schema {schema_name} checked or created')    
    


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()
        
def include_object(object, name, type_, reflected, compare_to):
    if type_ == 'table':
        if object.schema != get_settings().DB_SCHEMA:
            return False
    return True         


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    create_schemas_if_not_exists(connectable, get_settings().DB_SCHEMA)
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_schemas= True,
            version_table_schema= get_settings().DB_SCHEMA,
            include_object=include_object
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()