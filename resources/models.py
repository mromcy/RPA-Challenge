"""
The project's ORM models and status enums.

WARNING: importing this module opens a database connection.

The process_manager.process_run table belongs to another system and is
reflected from the database (autoload_with=engine) instead of being declared
here — keeping a local copy of a shared schema's definition is how drift
between automations begins. The price of that choice is that the reflection
happens at import time.

The practical consequence: resources.models and everything that imports it
(Utils/operation_db and execute) require a reachable PostgreSQL. The project's
other modules — settings, logs, read_file, Schemas and Modules — import with no
database at all, and that is why the unit tests can cover them.
"""

from datetime import datetime, timedelta

from sqlalchemy import ForeignKey, Interval, MetaData, Table, inspect
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column, registry
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from resources.database import engine
from resources.Schemas.item_run import ItemRunStatus
from resources.settings import get_settings

external_md = MetaData(schema='process_manager')
table_registry = registry()


def _ensure_process_run_exists() -> None:
    """
    Makes sure the central process_manager.process_run table exists before it
    is reflected.

    process_run is a CENTRAL dependency, shared by several automations and
    provisioned externally (outside this project's migrations). That is why it
    is reflected from the database rather than created here — creating a shared
    table from each bot would lead to schema drift and race conditions.

    This check exists only to fail fast with a clear message if the environment
    has not been provisioned yet, instead of a raw NoSuchTableError.
    """
    insp = inspect(engine)
    if 'process_manager' not in insp.get_schema_names():
        raise RuntimeError(
            "Schema 'process_manager' not found in the database.\n"
            "The central table 'process_manager.process_run' is a dependency "
            'shared between the automations and must be provisioned in advance '
            '(outside this project). Create the schema and the table in the '
            'environment before running the automation.'
        )
    if not insp.has_table('process_run', schema='process_manager'):
        raise RuntimeError(
            "Table 'process_manager.process_run' not found.\n"
            'It is a central dependency shared between the automations and must '
            'be created in advance (outside this project). Check as well that '
            'the database user has read permission on the process_manager '
            'schema.'
        )


# Fail early, and with a clear message, if the central dependency has not been
# provisioned
_ensure_process_run_exists()

process_run_tbl = Table(
    'process_run',
    table_registry.metadata,
    schema='process_manager',
    autoload_with=engine,
)


@table_registry.mapped
class ORMProcessRun:
    __table__ = process_run_tbl


schema_name = get_settings().DB_SCHEMA


@table_registry.mapped_as_dataclass
class ORMItemRun:
    __tablename__ = 'item_run'
    __table_args__ = {'schema': schema_name}

    item_id: Mapped[int] = mapped_column(init=False, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey('process_manager.process_run.run_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    process_name: Mapped[str]
    item_key: Mapped[str]
    area: Mapped[str]
    priority: Mapped[int]
    status: Mapped[ItemRunStatus] = mapped_column(
        PGEnum(
            ItemRunStatus,
            name='item_run_status',
            schema=schema_name,
            create_type=True,
        ),
        nullable=False,
    )
    tags: Mapped[str]
    resource_name: Mapped[str]
    attempt: Mapped[int]
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(init=False, server_default=func.now())
    started_at: Mapped[datetime] = mapped_column(nullable=True, default=None)
    last_updated_at: Mapped[datetime] = mapped_column(nullable=True, default=None)
    next_review_at: Mapped[datetime] = mapped_column(nullable=True, default=None)
    completed_at: Mapped[datetime] = mapped_column(nullable=True, default=None)
    total_work_time: Mapped[timedelta] = mapped_column(
        Interval, nullable=True, default=None
    )
    exception_at: Mapped[datetime] = mapped_column(nullable=True, default=None)
    exception_reason: Mapped[str] = mapped_column(nullable=True, default=None)


@table_registry.mapped_as_dataclass
class ORMItem:
    __tablename__ = 'item'
    __table_args__ = {'schema': schema_name}

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey(f'{schema_name}.item_run.item_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    First_Name: Mapped[str] = mapped_column(nullable=False)
    Last_Name: Mapped[str] = mapped_column(nullable=False)
    Company_Name: Mapped[str] = mapped_column(nullable=False)
    Role_in_Company: Mapped[str] = mapped_column(nullable=False)
    Address: Mapped[str] = mapped_column(nullable=False)
    Email: Mapped[str] = mapped_column(nullable=False)
    Phone_Number: Mapped[str] = mapped_column(nullable=False)
    result: Mapped[str] = mapped_column(nullable=True, default=None)
