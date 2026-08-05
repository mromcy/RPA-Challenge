"""
Comunicação com o BotCity Maestro.

Toda conversa com o orquestrador passa por aqui: conectar, ler os parâmetros da
task e reportar o desfecho. Os outros módulos entregam os dados e não montam
mensagem de painel — antes desta consolidação o formato da mensagem de falha
estava escrito em dois lugares, com um comentário confessando a duplicação.

Este módulo **não importa configuração nem banco**, e não deve importar: o
reportar_falha precisa funcionar justamente quando o config.json está ausente
ou o banco está fora do ar, que são duas das falhas que ele existe para relatar.

O robô se autentica pelo token de execução que o runner entrega na linha de
comando, e não por chave de API guardada em arquivo. Consequência: não existe
credencial de vida longa em repouso na máquina do robô. O caminho da chave de
API só faria sentido para um processo que **liga** para o orquestrador em vez de
ser chamado por ele — um portal interno que cria tasks, um vigia de pasta de
rede, um pipeline de CI — e este bot nunca está nessa posição.
"""

from collections.abc import Mapping
from typing import NamedTuple

from botcity.maestro import AutomationTaskFinishStatus, BotMaestroSDK


class Contagem(NamedTuple):
    """
    Os três números que o painel do Maestro exibe para uma execução.

    Andam sempre juntos — são exatamente o que o finish_task recebe —, então
    viajam como uma coisa só em vez de três parâmetros soltos.
    """

    total: int = 0
    processados: int = 0
    falhados: int = 0


def conectar() -> BotMaestroSDK:
    """
    Devolve o SDK pronto, funcionando nos dois modos de execução.

    O `from_sys_args()` resolve os dois sozinho: com quatro ou mais argumentos
    na linha de comando, lê server/task_id/token/organization **por posição** e
    conecta ao orquestrador; abaixo disso devolve uma instância local, com
    task_id vazio, e nenhuma chamada ao Maestro tem efeito.

    Returns:
        BotMaestroSDK: Conectado ao orquestrador ou em modo local.
    """
    maestro = BotMaestroSDK.from_sys_args()

    if not maestro.task_id:
        print('Executando em modo local (sem task_id).')

    return maestro


def obter_parametros_da_task(maestro: BotMaestroSDK) -> Mapping[str, object]:
    """
    Parâmetros informados ao disparar a task no painel.

    Em modo local devolve um dicionário vazio, o que poupa quem chama de checar
    se há execução: o resultado tem sempre o mesmo tipo.

    Args:
        maestro: SDK já conectado.

    Returns:
        Mapping[str, object]: Parâmetros da task, ou vazio em modo local.
    """
    if not maestro.task_id:
        return {}

    return maestro.get_execution().parameters


def reportar_conclusao(
    maestro: BotMaestroSDK,
    contagem: Contagem,
    driver: str,
    resultado: str,
) -> None:
    """
    Encerra a task que rodou até o fim, com o desfecho legível no painel.

    O status distingue os dois desfechos possíveis de uma execução completa:
    `SUCCESS` quando nenhum item falhou, `PARTIALLY_COMPLETED` quando a fila
    terminou mas houve itens com erro. `FAILED` fica reservado para a execução
    que **não** chegou ao fim — é o que o reportar_falha usa.

    A distinção importa para quem opera: "terminou, mas sete registros ficaram
    para trás" pede uma ação diferente de "não rodou".

    A mensagem leva o texto que o próprio site informou e o driver usado: é o
    que o operador precisa saber sem abrir log nenhum.

    Args:
        maestro: SDK já conectado. Sem task_id, não faz nada.
        contagem: Total, processados e falhados.
        driver: Nome do driver que executou.
        resultado: Texto do resultado informado pelo site.
    """
    if not maestro.task_id:
        return

    houve_falhas = contagem.falhados > 0
    status = (
        AutomationTaskFinishStatus.PARTIALLY_COMPLETED
        if houve_falhas
        else AutomationTaskFinishStatus.SUCCESS
    )
    abertura = 'Concluído com falhas' if houve_falhas else 'Concluído'

    maestro.finish_task(
        task_id=str(maestro.task_id),
        status=status,
        message=(
            f'{abertura} com {driver}. {resultado} '
            f'Processados: {contagem.processados} '
            f'- Falhados: {contagem.falhados} '
            f'- Total de itens: {contagem.total}'
        ),
        total_items=contagem.total,
        processed_items=contagem.processados,
        failed_items=contagem.falhados,
    )


def reportar_falha(
    maestro: BotMaestroSDK,
    erro: Exception,
    contagem: Contagem = Contagem(),
    driver: str = '',
) -> None:
    """
    Encerra a task como FAILED, com a causa real.

    Sem isto, uma falha de partida — `config.json` ausente, banco fora do ar,
    driver inválido no parâmetro da task — mata o processo antes de qualquer
    `finish_task`, e o painel mostra só *"An unexpected issue led to the task
    being terminated"*, que não diz a ninguém o que fazer.

    A mensagem leva o **tipo** da exceção junto do texto: `FileNotFoundError` e
    `ValueError` mandam a investigação para lugares diferentes. O stack completo
    fica de fora — cinquenta linhas num painel não ajudam ninguém — e continua
    gravado em `process_run.error_stack` e no arquivo de log.

    Args:
        maestro: SDK já conectado. Sem task_id, não faz nada.
        erro: Exceção que interrompeu a execução.
        contagem: Quanto havia sido processado até a falha. Numa falha de
            partida, zeros — nada chegou a rodar.
        driver: Driver em uso, quando já havia sido escolhido.
    """
    if not maestro.task_id:
        return

    sufixo = f' (driver: {driver})' if driver else ''

    maestro.finish_task(
        task_id=str(maestro.task_id),
        status=AutomationTaskFinishStatus.FAILED,
        message=f'{type(erro).__name__}: {erro}{sufixo}',
        total_items=contagem.total,
        processed_items=contagem.processados,
        failed_items=contagem.falhados,
    )
