"""
Operações de banco de dados para a tabela process_run.

Nesta primeira etapa, o módulo expõe apenas as operações necessárias
para rastrear o ciclo de vida de uma execução de processo:
- insert_process_run: cria um novo registro (raramente usado diretamente;
  prefira AddProcessRun para a criação inicial).
- update_process_run_status: atualiza status, timestamps e erros conforme
  a transição de estado.

Transições de status suportadas:
    SCHEDULED → RUNNING   : preenche started_at e stage_started_at
    RUNNING   → COMPLETED : preenche ended_at e calcula total_work_time
    RUNNING   → FAILED    : preenche ended_at, total_work_time, error_message e error_stack
    qualquer  → CANCELED  : preenche ended_at e total_work_time
"""

import traceback
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from resources.database import get_session
from resources.models import ItemRunStatus, ORMItem, ORMItemRun, ORMProcessRun, ProcessRunStatus
from resources.Schemas.item_run import Item, ItemInfo, ItemRun
from resources.Schemas.process_run import ProcessRun

# Timezone padrão de todos os timestamps registrados no banco
_TZ = ZoneInfo('America/Fortaleza')


class OperationDb:
    """
    Fachada de acesso ao banco de dados para operações de process_run.

    Todos os métodos são estáticos: a classe serve apenas como namespace
    organizado, sem estado interno.

    Exemplo de uso::

        db = OperationDb()
        db.update_process_run_status(run_id=1, status=ProcessRunStatus.RUNNING)
    """

    # ─────────────────────────────────────────────────────────────────────────
    # process_run — inserção
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def insert_process_run(process_run: ProcessRun) -> int:
        """
        Insere um novo registro na tabela process_run.

        Prefira usar AddProcessRun.execute() para a criação inicial do processo,
        pois ele já captura hostname e usuário automaticamente.
        Este método é útil para casos de uso avançados onde o schema
        ProcessRun já está montado externamente.

        Args:
            process_run: Schema Pydantic com os dados do processo.

        Returns:
            int: run_id gerado pelo banco de dados.
        """
        orm_run: Any = ORMProcessRun()
        orm_run.process_name = process_run.process_name
        orm_run.resource_name = process_run.resource_name
        orm_run.scheduled_by = process_run.scheduled_by
        orm_run.area = process_run.area
        orm_run.status = process_run.status

        with get_session() as session:
            session.add(orm_run)
            session.flush()
            run_id = orm_run.run_id

        return run_id

    # ─────────────────────────────────────────────────────────────────────────
    # process_run — atualização de status
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def update_process_run_status(
        run_id: int,
        status: ProcessRunStatus,
        error_message: str | None = None,
        error_stack: str | None = None,
    ) -> None:
        """
        Atualiza o status de uma execução e preenche os campos de timestamp
        conforme a transição de estado.

        Comportamento por status:

        - **RUNNING**: define started_at (se ainda None) e stage_started_at
          com o momento atual; limpa campos de erro.
        - **COMPLETED**: define ended_at e calcula total_work_time;
          limpa campos de erro.
        - **FAILED**: define ended_at, calcula total_work_time e persiste
          error_message e error_stack. Caso não sejam fornecidos, usa
          mensagens padrão para garantir que o registro nunca fique vazio.
        - **CANCELED**: define ended_at e calcula total_work_time.
        - **SCHEDULED**: apenas atualiza o status.

        Args:
            run_id: Identificador do registro a ser atualizado.
            status: Novo status da execução (valor do enum ProcessRunStatus).
            error_message: Mensagem de erro legível (apenas para FAILED).
            error_stack: Stacktrace completo do erro (apenas para FAILED).

        Raises:
            NoResultFound: Se não existir um registro com o run_id informado.
            ValueError: Se o status fornecido não for válido.
        """
        now = datetime.now(_TZ)

        with get_session() as session:
            pr: Any = session.execute(
                select(ORMProcessRun).where(ORMProcessRun.run_id == run_id)  # type: ignore[attr-defined]
            ).scalar_one_or_none()

            if pr is None:
                raise NoResultFound(
                    f'ProcessRun com run_id={run_id} não encontrado no banco de dados.'
                )

            pr.status = status.value

            match status:
                case ProcessRunStatus.RUNNING:
                    # Preserva o started_at original caso o processo já tenha sido iniciado
                    if pr.started_at is None:
                        pr.started_at = now
                    pr.stage_started_at = now
                    # Garante que erros de execuções anteriores não persistam
                    pr.error_message = None
                    pr.error_stack = None

                case ProcessRunStatus.COMPLETED:
                    if pr.started_at is None:
                        pr.started_at = now
                    pr.ended_at = now
                    pr.total_work_time = pr.ended_at - pr.started_at.astimezone(_TZ)
                    pr.error_message = None
                    pr.error_stack = None

                case ProcessRunStatus.FAILED:
                    if pr.started_at is None:
                        pr.started_at = now
                    pr.ended_at = now
                    pr.total_work_time = pr.ended_at - pr.started_at.astimezone(_TZ)
                    # Nunca deixa o campo de erro vazio para facilitar diagnóstico
                    pr.error_message = (
                        error_message or 'Processo falhou sem mensagem de erro.'
                    )
                    pr.error_stack = error_stack or 'Stacktrace indisponível.'

                case ProcessRunStatus.CANCELED:
                    if pr.started_at is None:
                        pr.started_at = now
                    pr.ended_at = now
                    pr.total_work_time = pr.ended_at - pr.started_at.astimezone(_TZ)

                case ProcessRunStatus.SCHEDULED:
                    pass  # Apenas registra o novo status; sem mudanças de timestamp

            session.flush()

    # ─────────────────────────────────────────────────────────────────────────
    # item_run — consulta e atualização de status
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_queued_items_by_run(run_id: int) -> list[ItemInfo]:
        """
        Retorna todos os itens com status QUEUED do run informado.

        Faz join entre process_run, item_run e item para montar o ItemInfo
        completo, que será usado pelo executar_challenge para processar cada
        formulário e atualizar o status no banco.

        Args:
            run_id: Identificador do processo em execução.

        Returns:
            list[ItemInfo]: Itens prontos para processamento, ordenados por item_id.
        """
        with get_session() as session:
            stmt = (
                select(ORMProcessRun, ORMItemRun, ORMItem)
                .join(ORMItemRun, ORMItemRun.run_id == ORMProcessRun.run_id)  # type: ignore[attr-defined]
                .join(ORMItem, ORMItem.item_id == ORMItemRun.item_id)
                .where(
                    ORMProcessRun.run_id == run_id,  # type: ignore[attr-defined]
                    ORMItemRun.status == ItemRunStatus.QUEUED.value,
                )
                .order_by(ORMItemRun.item_id)
            )
            rows = session.execute(stmt).all()
            return [
                ItemInfo(
                    process_run=ProcessRun.model_validate(pr),
                    item_run=ItemRun.model_validate(ir),
                    item=Item.model_validate(it),
                )
                for pr, ir, it in rows
            ]

    @staticmethod
    def update_item_run_status(
        item_id: int,
        status: ItemRunStatus,
        exception_reason: str | None = None,
    ) -> None:
        """
        Atualiza o status de um item_run e preenche os campos de timestamp
        conforme a transição de estado.

        Comportamento por status:

        - **PROCESSING**: define started_at e last_updated_at.
        - **COMPLETED**: define completed_at, last_updated_at e calcula total_work_time.
        - **FAILED**: define exception_at, exception_reason, last_updated_at
          e calcula total_work_time.

        Args:
            item_id: Identificador do item_run a ser atualizado.
            status: Novo status (valor do enum ItemRunStatus).
            exception_reason: Mensagem de erro (apenas para FAILED).

        Raises:
            NoResultFound: Se não existir item_run com o item_id informado.
        """
        now = datetime.now(_TZ)

        with get_session() as session:
            ir: Any = session.execute(
                select(ORMItemRun).where(ORMItemRun.item_id == item_id)  # type: ignore[attr-defined]
            ).scalar_one_or_none()

            if ir is None:
                raise NoResultFound(
                    f'ItemRun com item_id={item_id} não encontrado no banco de dados.'
                )

            ir.status = status.value

            match status:
                case ItemRunStatus.PROCESSING:
                    ir.started_at = now
                    ir.last_updated_at = now

                case ItemRunStatus.COMPLETED:
                    ir.completed_at = now
                    ir.last_updated_at = now
                    if ir.started_at:
                        ir.total_work_time = now - ir.started_at.astimezone(_TZ)

                case ItemRunStatus.FAILED:
                    ir.exception_at = now
                    ir.last_updated_at = now
                    ir.exception_reason = exception_reason or 'Erro sem mensagem.'
                    if ir.started_at:
                        ir.total_work_time = now - ir.started_at.astimezone(_TZ)

            session.flush()

    @staticmethod
    def update_items_result(item_ids: list[int], result: str) -> None:
        """
        Grava o resultado final do challenge na coluna result de cada item.

        Chamado após capturar_resultado(), quando o texto exibido pelo desafio
        já está disponível. O mesmo resultado é registrado em todos os itens
        do run, pois o RPA Challenge retorna uma pontuação única para a execução.

        Args:
            item_ids: Lista de item_ids (FK em item) a serem atualizados.
            result: Texto do resultado capturado na página do challenge.
        """
        with get_session() as session:
            for item_id in item_ids:
                it: Any = session.execute(
                    select(ORMItem).where(ORMItem.item_id == item_id)  # type: ignore[attr-defined]
                ).scalar_one_or_none()
                if it is not None:
                    it.result = result
            session.flush()
