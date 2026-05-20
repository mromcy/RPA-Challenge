"""
1 - Funções de passos da execução do RPA Challenge.
2 - Responsável pela leitura de dados e pela automação do formulário.
3 - Recebe (page, logs) como parâmetros, seguindo o padrão do projeto.
"""

import pandas as pd
from playwright.sync_api import Page

from resources.models import ItemRunStatus
from resources.Modules.challenge import Challenge
from resources.Schemas.item_run import ItemInfo
from resources.Tools.logs import Logs
from resources.Utils.ler_arquivo import LerArquivo
from resources.Utils.operation_db import OperationDb


def ler_dados(logs: Logs) -> pd.DataFrame:
    """
    Lê os arquivos .xlsx da pasta de entrada e retorna um DataFrame consolidado.

    Args:
        logs: Instância de Logs para registro das operações.

    Returns:
        DataFrame com os dados tratados e prontos para uso.
    """
    logs.info("Lendo arquivo de entrada.")
    dados = LerArquivo(logs).ler_arquivo()
    logs.info(f"{len(dados)} registros carregados com sucesso.")
    return dados


def executar_challenge(
    page: Page,
    logs: Logs,
    items: list[ItemInfo],
    url: str,
    db: OperationDb,
) -> tuple[int, int]:
    """
    Executa o fluxo completo do RPA Challenge: navega para a URL, inicia o desafio
    e preenche o formulário para cada item lido do banco.

    Para cada item, atualiza o status no banco:
    QUEUED → PROCESSING → COMPLETED (ou FAILED em caso de erro).

    Args:
        page: Instância da página do Playwright.
        logs: Instância de Logs para registro das operações.
        items: Lista de ItemInfo lidos do banco com status QUEUED.
        url: URL do RPA Challenge.
        db: Instância de OperationDb para atualização de status por item.

    Returns:
        tuple[int, int]: (processados_com_sucesso, processados_com_falha)
    """
    total = len(items)
    logs.info("Iniciando desafio.")
    challenge = Challenge(page, logs)
    challenge.iniciar_desafio(url)

    item_ids: list[int] = []
    processed = failed = 0

    for i, item_info in enumerate(items, 1):
        item_id = item_info.item_run.item_id  # type: ignore[union-attr]
        logs.info(f"Preenchendo formulário {i}/{total}.")

        db.update_item_run_status(item_id, ItemRunStatus.PROCESSING)
        try:
            challenge.preencher_formulario(item_info.item)  # type: ignore[arg-type]
            db.update_item_run_status(item_id, ItemRunStatus.COMPLETED)
            item_ids.append(item_id)
            processed += 1

        except Exception as e:
            db.update_item_run_status(
                item_id,
                ItemRunStatus.FAILED,
                exception_reason=str(e),
            )
            failed += 1
            raise

    logs.info("Aguardando resultado final.")
    resultado = challenge.capturar_resultado()
    if resultado:
        db.update_items_result(item_ids, resultado)
    logs.info("Execução concluída com sucesso.")
    return processed, failed
