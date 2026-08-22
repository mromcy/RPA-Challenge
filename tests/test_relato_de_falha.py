"""
Testes da comunicação com o BotCity Maestro (Tools/botcity.py).

O módulo não importa configuração nem banco — requisito, não coincidência: o
reportar_falha precisa funcionar justamente quando o config.json falta ou o
banco está fora do ar. É isso que torna estes testes possíveis sem subir nada.
"""

from unittest.mock import MagicMock

from botcity.maestro import AutomationTaskFinishStatus

from resources.Tools.botcity import (
    Contagem,
    obter_parametros_da_task,
    reportar_conclusao,
    reportar_falha,
)


def test_execucao_local_nao_reporta_nada():
    """Sem task_id não há orquestrador esperando resposta."""
    maestro = MagicMock(task_id=None)

    reportar_falha(maestro, ValueError('qualquer coisa'))

    maestro.finish_task.assert_not_called()


def test_reporta_falha_com_o_tipo_e_o_texto_da_excecao():
    """
    O tipo entra junto do texto porque manda a investigação para lugares
    diferentes: FileNotFoundError é problema de implantação, ValueError é
    parâmetro errado na task.
    """
    maestro = MagicMock(task_id='24475890')

    reportar_falha(maestro, FileNotFoundError('config.json não encontrado'))

    maestro.finish_task.assert_called_once()
    argumentos = maestro.finish_task.call_args.kwargs
    assert argumentos['status'] == AutomationTaskFinishStatus.FAILED
    assert argumentos['task_id'] == '24475890'
    assert argumentos['message'] == ('FileNotFoundError: config.json não encontrado')


def test_task_id_numerico_vira_texto():
    """O SDK espera task_id como str; o runner pode entregar outro tipo."""
    maestro = MagicMock(task_id=24475890)

    reportar_falha(maestro, RuntimeError('falhou'))

    assert maestro.finish_task.call_args.kwargs['task_id'] == '24475890'


def test_falha_leva_o_driver_quando_ja_havia_sido_escolhido():
    """
    Numa falha de partida não há driver ainda, e o sufixo não aparece — o
    campo em branco seria ruído numa mensagem que o operador lê às pressas.
    """
    maestro = MagicMock(task_id='1')

    reportar_falha(maestro, RuntimeError('site fora do ar'), driver='selenium')

    mensagem = maestro.finish_task.call_args.kwargs['message']
    assert mensagem == 'RuntimeError: site fora do ar (driver: selenium)'


def test_falha_sem_driver_nao_deixa_sufixo_vazio():
    maestro = MagicMock(task_id='1')

    reportar_falha(maestro, RuntimeError('falhou'))

    assert maestro.finish_task.call_args.kwargs['message'] == ('RuntimeError: falhou')


def test_falha_de_partida_reporta_contagem_zerada():
    """Nada chegou a rodar, e o painel precisa mostrar isso."""
    maestro = MagicMock(task_id='1')

    reportar_falha(maestro, ValueError('config'))

    argumentos = maestro.finish_task.call_args.kwargs
    assert argumentos['total_items'] == 0
    assert argumentos['processed_items'] == 0
    assert argumentos['failed_items'] == 0


def test_conclusao_sem_falhas_leva_resultado_driver_e_contagem():
    maestro = MagicMock(task_id='42')
    contagem = Contagem(total=10, processados=10, falhados=0)

    reportar_conclusao(
        maestro,
        contagem,
        driver='selenium',
        resultado='Your success rate is 100% ( 70 out of 70 fields)',
    )

    argumentos = maestro.finish_task.call_args.kwargs
    assert argumentos['status'] == AutomationTaskFinishStatus.SUCCESS
    assert 'Concluído com selenium.' in argumentos['message']
    assert '100% ( 70 out of 70 fields)' in argumentos['message']
    assert argumentos['total_items'] == contagem.total
    assert argumentos['processed_items'] == contagem.processados


def test_conclusao_com_itens_falhados_vira_parcialmente_concluida():
    """
    A fila terminou, mas nem todos os itens passaram. `FAILED` seria mentira —
    ele diz "não rodou" —, e `SUCCESS` esconderia os registros que ficaram para
    trás. Para o operador, "terminou com falhas" pede ação diferente das duas.
    """
    maestro = MagicMock(task_id='42')
    contagem = Contagem(total=10, processados=7, falhados=3)

    reportar_conclusao(maestro, contagem, driver='playwright', resultado='70%')

    argumentos = maestro.finish_task.call_args.kwargs
    assert argumentos['status'] == AutomationTaskFinishStatus.PARTIALLY_COMPLETED
    assert 'Concluído com falhas' in argumentos['message']
    assert argumentos['processed_items'] == contagem.processados
    assert argumentos['failed_items'] == contagem.falhados


def test_conclusao_em_execucao_local_nao_reporta():
    maestro = MagicMock(task_id=None)

    reportar_conclusao(maestro, Contagem(), driver='playwright', resultado='ok')

    maestro.finish_task.assert_not_called()


def test_parametros_em_execucao_local_sao_um_dicionario_vazio():
    """
    Devolver sempre o mesmo tipo poupa quem chama de checar se há execução —
    era esse `if` que existia dentro do Execute antes desta consolidação.
    """
    maestro = MagicMock(task_id=None)

    assert obter_parametros_da_task(maestro) == {}
    maestro.get_execution.assert_not_called()


def test_parametros_vem_da_execucao_quando_orquestrado():
    maestro = MagicMock(task_id='42')
    maestro.get_execution.return_value = MagicMock(parameters={'driver': 'selenium'})

    assert obter_parametros_da_task(maestro) == {'driver': 'selenium'}


def test_mensagem_do_driver_invalido_chega_inteira():
    """
    O caso que motivou tudo isto: antes, este erro morria no __init__ e o
    painel mostrava só a mensagem genérica do runner.
    """
    maestro = MagicMock(task_id='1')
    erro = ValueError(
        'Parâmetro "driver" da task com valor desconhecido: \'cypress\'. '
        'Disponíveis: playwright, selenium.'
    )

    reportar_falha(maestro, erro)

    mensagem = maestro.finish_task.call_args.kwargs['message']
    assert mensagem.startswith('ValueError: ')
    assert 'cypress' in mensagem
    assert 'playwright, selenium' in mensagem
