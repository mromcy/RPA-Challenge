"""
Modelos ORM e enums de status do projeto.

ATENÇÃO: importar este módulo abre conexão com o banco de dados.

A tabela process_manager.process_run pertence a outro sistema e é refletida do banco
(autoload_with=engine) em vez de declarada aqui — manter uma cópia local da definição
de um schema compartilhado é como o drift entre as automações começa. O preço dessa
escolha é que a reflexão acontece no import.

Consequência prática: resources.models e tudo que o importa (Utils/operation_db e
execute) exigem um PostgreSQL acessível. Os demais módulos do projeto — settings,
logs, ler_arquivo, Schemas e Modules — importam sem banco nenhum, e é por isso que
os testes unitários conseguem cobri-los.
"""

import enum
from datetime import datetime, timedelta

from sqlalchemy import ForeignKey, Interval, MetaData, Table, inspect
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column, registry
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from resources.database import engine
from resources.settings import Settings

external_md = MetaData(schema='process_manager')
table_registry = registry()


def _verificar_process_run_existe() -> None:
    """
    Garante que a tabela central process_manager.process_run existe antes de refleti-la.

    A process_run é uma dependência CENTRAL, compartilhada por várias automações e
    provisionada externamente (fora das migrations deste projeto). Por isso ela é
    refletida do banco, não criada aqui — criar uma tabela compartilhada a partir de
    cada bot levaria a drift de schema e race conditions.

    Esta verificação existe apenas para falhar rápido com uma mensagem clara caso o
    ambiente ainda não tenha sido provisionado, em vez de um NoSuchTableError cru.
    """
    insp = inspect(engine)
    if 'process_manager' not in insp.get_schema_names():
        raise RuntimeError(
            "Schema 'process_manager' não encontrado no banco de dados.\n"
            "A tabela central 'process_manager.process_run' é uma dependência "
            'compartilhada entre as automações e deve ser provisionada previamente '
            '(fora deste projeto). Crie o schema e a tabela no ambiente antes de '
            'executar a automação.'
        )
    if not insp.has_table('process_run', schema='process_manager'):
        raise RuntimeError(
            "Tabela 'process_manager.process_run' não encontrada.\n"
            'Ela é uma dependência central compartilhada entre as automações e deve '
            'ser criada previamente (fora deste projeto). Verifique também se o '
            'usuário do banco tem permissão de leitura no schema process_manager.'
        )


# Falha cedo e com mensagem clara se a dependência central não estiver provisionada
_verificar_process_run_existe()

process_run_tbl = Table(
    'process_run',
    table_registry.metadata,
    schema='process_manager',
    autoload_with=engine,
)


@table_registry.mapped
class ORMProcessRun:
    __table__ = process_run_tbl


schema_name = Settings().DB_SCHEMA  # type: ignore[call-arg]


class ProcessRunStatus(str, enum.Enum):
    SCHEDULED = 'SCHEDULED'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CANCELED = 'CANCELED'


class ItemRunStatus(str, enum.Enum):
    QUEUED = 'QUEUED'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    EXCEPTION = 'EXCEPTION'
    ON_HOLD = 'ON_HOLD'
    DEFERRED = 'DEFERRED'


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
