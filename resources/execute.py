"""
Orquestrador principal da execução do RPA Challenge.

Responsabilidades:
- Registrar o início e o fim da execução na tabela process_run.
- Carregar os dados de entrada (XLSX).
- Iniciar o navegador e executar o preenchimento do formulário.
- Garantir que o status no banco reflita o resultado real da execução,
  seja COMPLETED em caso de sucesso ou FAILED com detalhes do erro.
"""

import traceback

from botcity.maestro import AutomationTaskFinishStatus, BotMaestroSDK
from playwright.sync_api import sync_playwright

from resources.Executers.execute_challenge import executar_challenge, ler_dados
from resources.models import ProcessRunStatus
from resources.settings import get_settings
from resources.Tools.add_process_run import AddProcessRun
from resources.Tools.botcity import login  # noqa
from resources.Tools.logs import Logs
from resources.Utils.create_items import create_items
from resources.Utils.operation_db import OperationDb


class Execute:
    """
    Classe responsável por orquestrar toda a execução do bot.

    O construtor já cria o registro de execução no banco com status SCHEDULED,
    garantindo rastreabilidade desde o instante em que o processo é iniciado.

    Atributos:
        maestro: SDK do BotCity para integração com o servidor de automação.
        logs: Logger combinado (console, arquivo e banco).
        settings: Configurações carregadas do config.json.
        db: Fachada de operações de banco de dados para process_run e item_run.
        run_id: Identificador único desta execução, gerado no banco ao iniciar.
    """

    def __init__(self):
        self.maestro = BotMaestroSDK()
        self.maestro = BotMaestroSDK.from_sys_args()

        if not self.maestro.task_id:
            print('Executando em modo local (sem task_id).')
            self.execution = None
        else:
            self.execution = self.maestro.get_execution()

        self.logs = Logs(self.maestro)
        self.settings = get_settings()
        self.db = OperationDb()

        # Cria o registro inicial no banco; a partir daqui, run_id identifica
        # esta execução em todas as tabelas relacionadas
        self.run_id = AddProcessRun().execute()
        self.logs.info(
            f'Execução registrada no banco com run_id={self.run_id} (SCHEDULED)'
        )

    def execute(self) -> None:
        """
        Executa o fluxo completo do RPA Challenge.

        Fluxo:
            1. Atualiza process_run para RUNNING.
            2. Lê os dados do arquivo XLSX de entrada.
            3. Persiste os dados nas tabelas item_run e item (status QUEUED).
            4. Lê os itens do banco prontos para processamento.
            5. Abre o navegador e executa o preenchimento do formulário,
               atualizando o status de cada item no banco.
            6. Atualiza process_run para COMPLETED em caso de sucesso.
            7. Em caso de qualquer exceção, atualiza para FAILED com
               mensagem e stacktrace e re-lança o erro.
        """
        self.db.update_process_run_status(self.run_id, ProcessRunStatus.RUNNING)
        self.logs.info(f'run_id={self.run_id} → RUNNING')

        total = processed = failed = 0

        try:
            # Lê o Excel e persiste item_run + item no banco
            dados = ler_dados(self.logs)
            item_ids = create_items(dados, self.run_id)
            self.logs.info(f'{len(item_ids)} itens persistidos no banco (QUEUED).')

            # Lê do banco os itens prontos para processamento
            items = self.db.get_queued_items_by_run(self.run_id)
            total = len(items)
            self.logs.info(f'{total} itens carregados do banco para processamento.')

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False, args=['--start-maximized'])
                page = browser.new_page(no_viewport=True)
                processed, failed = executar_challenge(
                    page, self.logs, items, self.settings.PATH_URL, self.db
                )
                browser.close()

            self.db.update_process_run_status(self.run_id, ProcessRunStatus.COMPLETED)
            self.logs.info(f'run_id={self.run_id} → COMPLETED')

            if self.maestro.task_id:
                self.maestro.finish_task(
                    task_id=str(self.maestro.task_id),
                    status=AutomationTaskFinishStatus.SUCCESS,
                    message=(
                        f'Execução concluída com sucesso. Processados: {processed} '
                        f'- Falhados: {failed} - Total de itens: {total}'
                    ),
                    total_items=total,
                    processed_items=processed,
                    failed_items=failed,
                )

        except Exception as e:
            # Captura o stacktrace completo para diagnóstico no banco
            stack = traceback.format_exc()
            self.db.update_process_run_status(
                self.run_id,
                ProcessRunStatus.FAILED,
                error_message=str(e),
                error_stack=stack,
            )
            self.logs.error(e)
            self.logs.info(f'run_id={self.run_id} → FAILED')

            if self.maestro.task_id:
                self.maestro.finish_task(
                    task_id=str(self.maestro.task_id),
                    status=AutomationTaskFinishStatus.FAILED,
                    message=str(e),
                    total_items=total,
                    processed_items=processed,
                    failed_items=failed,
                )
            raise
