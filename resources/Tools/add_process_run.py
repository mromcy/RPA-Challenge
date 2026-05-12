"""
Criação do registro inicial de execução do processo.

Este módulo é o ponto de entrada para o rastreamento de execuções:
ele insere um registro com status SCHEDULED na tabela process_run e
retorna o run_id que será usado por toda a execução subsequente.
"""

import getpass
import socket
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from resources.database import get_session
from resources.models import ORMProcessRun, ProcessRunStatus
from resources.settings import Settings

_TZ = ZoneInfo('America/Fortaleza')


class AddProcessRun:
    """
    Responsável por criar o registro inicial de execução na tabela process_run.

    Deve ser instanciada uma vez no início de cada execução do bot.
    O run_id retornado por execute() deve ser propagado para todos os
    módulos que precisam atualizar o status da execução.

    Exemplo de uso::

        run_id = AddProcessRun().execute()
        # run_id agora está disponível para update de status

    """

    def execute(self) -> int:
        """
        Cria um novo registro de execução e retorna seu identificador.

        Returns:
            int: run_id do registro criado (status inicial: SCHEDULED).
        """
        return self.__create_process_run()

    @staticmethod
    def __create_process_run() -> int:
        """
        Insere o registro ORMProcessRun na tabela process_run.

        Captura automaticamente o hostname da máquina e o usuário do SO,
        garantindo rastreabilidade sem necessidade de configuração manual.

        Returns:
            int: run_id gerado pelo banco de dados.
        """
        settings = Settings()  # type: ignore[call-arg]

        now = datetime.now(_TZ)

        # Atribuição por propriedade em vez de kwargs no construtor:
        # o __init__ do ORMProcessRun é gerado em runtime pelo SQLAlchemy
        # e o Pyright não consegue inspecioná-lo, gerando falsos "No parameter named X".
        process_run: Any = ORMProcessRun()
        process_run.process_name = settings.PROJECT_NAME
        process_run.resource_name = socket.gethostname()
        process_run.scheduled_by = getpass.getuser()
        process_run.area = settings.AREA
        process_run.status = ProcessRunStatus.SCHEDULED.value
        # autoload_with não detecta o DEFAULT now() do PostgreSQL automaticamente,
        # então fornecemos os timestamps explicitamente para evitar NotNullViolation
        process_run.created_at = now
        process_run.updated_at = now

        with get_session() as session:
            session.add(process_run)
            # flush envia o INSERT ao banco sem encerrar a transação,
            # permitindo ler o run_id gerado antes do commit implícito do context manager
            session.flush()
            run_id = process_run.run_id

        return run_id
