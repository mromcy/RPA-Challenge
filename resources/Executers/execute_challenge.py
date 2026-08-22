"""
1 - Funções de passos da execução do RPA Challenge.
2 - Responsável pela leitura de dados e pela automação do formulário.
3 - Recebe (driver, logs) como parâmetros, seguindo o padrão do projeto.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from resources.Drivers.base import BrowserDriver
from resources.Modules.challenge import Challenge
from resources.Schemas.item_run import ItemInfo, ItemRunStatus
from resources.Tools.logs import Logs
from resources.Utils.ler_arquivo import LerArquivo

# O OperationDb aparece só na assinatura de executar_challenge; em runtime quem
# chega aqui é o objeto pronto, vindo do execute.py. Importá-lo de verdade traria
# junto o resources.models, que conecta no banco durante o import — e este módulo
# passaria a exigir PostgreSQL para ser importado, inclusive pelos testes, que
# passam um dublê no lugar. O from __future__ import annotations acima é o que
# permite a anotação sobreviver sem o import: ela não é avaliada em tempo de
# execução.
if TYPE_CHECKING:
    from resources.Utils.operation_db import OperationDb


def ler_dados(logs: Logs) -> pd.DataFrame:
    """
    Lê os arquivos .xlsx da pasta de entrada e retorna um DataFrame consolidado.

    Args:
        logs: Instância de Logs para registro das operações.

    Returns:
        DataFrame com os dados tratados e prontos para uso.
    """
    logs.info('Lendo arquivo de entrada.')
    dados = LerArquivo(logs).ler_arquivo()
    logs.info(f'{len(dados)} registros carregados com sucesso.')
    return dados


def executar_challenge(
    driver: BrowserDriver,
    logs: Logs,
    items: list[ItemInfo],
    url: str,
    db: OperationDb,
) -> str:
    """
    Executa o fluxo completo do RPA Challenge: navega para a URL, inicia o desafio
    e preenche o formulário para cada item lido do banco.

    Para cada item, atualiza o status no banco:
    QUEUED → PROCESSING → COMPLETED (ou FAILED em caso de erro).

    **A falha de um item não interrompe os demais.** O erro é gravado no
    `item_run` daquele item, contabilizado, e a fila segue. É o comportamento que
    justifica manter estado por item: numa carga de 5.000 registros, um dado
    ruim no meio não pode impedir os seguintes de serem tentados. Só falhas que
    inviabilizam a execução inteira — navegador que não sobe, site fora do ar —
    sobem e interrompem tudo.

    Args:
        driver: Implementação de BrowserDriver (Playwright, Selenium, ...).
        logs: Instância de Logs para registro das operações.
        items: Lista de ItemInfo lidos do banco com status QUEUED.
        url: URL do RPA Challenge.
        db: Instância de OperationDb para atualização de status por item.

    Returns:
        str: Texto que o próprio site informa ao final. Sobe até o orquestrador
            para o operador ver o desfecho sem abrir o log.

            **Quantos itens deram certo não é devolvido aqui de propósito.** Cada
            transição é gravada no `item_run` no instante em que acontece, e é de
            lá que a contagem é lida — um número em memória para de ser atualizado
            se uma falha de execução interromper o laço, e o painel passaria a
            mostrar zeros com dezenas de itens já concluídos no banco.
    """
    total = len(items)
    logs.info('Iniciando desafio.')
    challenge = Challenge(driver, logs)
    challenge.iniciar_desafio(url)

    item_ids: list[int] = []

    for i, item_info in enumerate(items, 1):
        item_id = item_info.item_run.item_id  # type: ignore[union-attr]
        logs.info(f'Preenchendo formulário {i}/{total}.')

        db.update_item_run_status(item_id, ItemRunStatus.PROCESSING)
        try:
            challenge.preencher_formulario(item_info.item)  # type: ignore[arg-type]
            db.update_item_run_status(item_id, ItemRunStatus.COMPLETED)
            item_ids.append(item_id)

        except Exception as e:
            # A fila continua: um registro ruim não derruba os outros. É a razão
            # de existir estado por item — sem isto, o item 3.200 de 5.000
            # impediria os 1.800 seguintes de sequer serem tentados.
            db.update_item_run_status(
                item_id,
                ItemRunStatus.FAILED,
                exception_reason=str(e),
            )
            logs.error(e)

    logs.info('Aguardando resultado final.')
    resultado = challenge.capturar_resultado()
    if resultado:
        db.update_items_result(item_ids, resultado)
    logs.info('Execução concluída com sucesso.')

    return resultado
