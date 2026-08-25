"""
The project's ORM models.

WARNING: importing this module opens a database connection. process_run is
reflected from the database rather than declared here, because it is shared
with other automations and provisioned outside this project - keeping a local
copy of a shared schema is how drift begins. The price is that the reflection
runs at import time, which is why execute.py wraps its import in a try.
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
    Fails fast, with a readable message, when process_manager.process_run has
    not been provisioned - instead of a raw NoSuchTableError from the
    reflection below.
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
