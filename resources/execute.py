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

from botcity.maestro import BotMaestroSDK

from resources.Drivers.factory import criar_driver, resolver_driver
from resources.Executers.execute_challenge import executar_challenge, ler_dados
from resources.models import ProcessRunStatus
from resources.settings import get_settings
from resources.Tools.add_process_run import AddProcessRun
from resources.Tools.botcity import (
    Contagem,
    obter_parametros_da_task,
    reportar_conclusao,
    reportar_falha,
)
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

    def __init__(self, maestro: BotMaestroSDK, driver: str | None = None):
        """
        Args:
            maestro: SDK já inicializado pelo ponto de entrada. Recebido pronto,
                e não criado aqui, para não abrir uma segunda conexão com o
                orquestrador — o bot.py precisa do SDK antes desta classe
                existir, para conseguir reportar falhas de partida.
            driver: 'playwright' ou 'selenium', vindo da linha de comando.
                Omitido, o driver é decidido em três camadas — ver
                Drivers.factory.resolver_driver.
        """
        self.maestro = maestro
        parametros_da_task = obter_parametros_da_task(maestro)

        self.logs = Logs(self.maestro)
        self.settings = get_settings()
        self.driver_escolhido = resolver_driver(driver, parametros_da_task)

        # Sem argumento na linha de comando, um driver escolhido só pode ter
        # vindo do parâmetro da task — e registrar a origem poupa quem investiga
        # de conferir três lugares para saber por que aquele driver rodou.
        if self.driver_escolhido and not driver:
            self.logs.info(
                f'Driver definido pelo parâmetro da task: {self.driver_escolhido}.'
            )

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

        total = 0
        resultado = ''
        nome_do_driver = self.driver_escolhido or self.settings.DRIVER

        try:
            # Lê o Excel e persiste item_run + item no banco
            dados = ler_dados(self.logs)
            item_ids = create_items(dados, self.run_id)
            self.logs.info(f'{len(item_ids)} itens persistidos no banco (QUEUED).')

            # Lê do banco os itens prontos para processamento
            items = self.db.get_queued_items_by_run(self.run_id)
            total = len(items)
            self.logs.info(f'{total} itens carregados do banco para processamento.')

            # Janela visível: o operador acompanha o robô preenchendo o formulário.
            driver = criar_driver(self.driver_escolhido, headless=False)
            nome_do_driver = driver.nome
            self.logs.info(f'Driver selecionado: {driver.nome}.')
            try:
                resultado = executar_challenge(
                    driver, self.logs, items, self.settings.PATH_URL, self.db
                )
            finally:
                # Falha ao fechar vira aviso: mascarar o erro original com um
                # problema de limpeza faria o diagnóstico apontar para o lugar
                # errado.
                try:
                    driver.fechar()
                except Exception as erro_de_limpeza:
                    self.logs.warning(f'Falha ao fechar o navegador: {erro_de_limpeza}')

            self.db.update_process_run_status(self.run_id, ProcessRunStatus.COMPLETED)
            self.logs.info(f'run_id={self.run_id} → COMPLETED')

            processados, falhados = self.db.contar_processados_e_falhados(self.run_id)
            reportar_conclusao(
                self.maestro,
                Contagem(total, processados, falhados),
                nome_do_driver,
                resultado,
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

            # A consulta roda enquanto tentamos reportar outra exceção: deixá-la
            # estourar mascararia o problema original, que é o que interessa.
            try:
                processados, falhados = self.db.contar_processados_e_falhados(self.run_id)
            except Exception as erro_de_consulta:
                self.logs.warning(f'Não foi possível contar os itens: {erro_de_consulta}')
                processados = falhados = 0

            reportar_falha(
                self.maestro,
                e,
                Contagem(total, processados, falhados),
                nome_do_driver,
            )
            raise
