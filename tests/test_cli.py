"""
Testes da leitura de argumentos de linha de comando (resources/cli.py).

O que estes testes protegem: o BotMaestroSDK.from_sys_args() lê a linha de
comando **por posição**, desempacotando sys.argv[1:] como
(server, task_id, token, organization). Qualquer argumento nosso deixado ali
desloca as posições e faz o robô se conectar ao lugar errado.
"""

import sys

import pytest

from resources.cli import obter_driver_dos_argumentos, separar_driver

MAESTRO = ['https://servidor.botcity', '12345', 'token-secreto', 'minha-org']


def test_sem_driver_devolve_none_e_nao_altera_a_linha_de_comando():
    argv = ['bot.py', *MAESTRO]

    driver, restante = separar_driver(argv)

    assert driver is None
    assert restante == argv


def test_driver_depois_dos_argumentos_do_maestro():
    argv = ['bot.py', *MAESTRO, '--driver', 'selenium']

    driver, restante = separar_driver(argv)

    assert driver == 'selenium'
    assert restante == ['bot.py', *MAESTRO]


def test_driver_antes_dos_argumentos_do_maestro_preserva_a_ordem():
    """
    O caso que justifica a limpeza: sem remover o --driver, o SDK leria
    server='--driver' e task_id='selenium'.
    """
    argv = ['bot.py', '--driver', 'selenium', *MAESTRO]

    driver, restante = separar_driver(argv)

    assert driver == 'selenium'
    assert restante == ['bot.py', *MAESTRO]


def test_execucao_local_apenas_com_driver():
    driver, restante = separar_driver(['bot.py', '--driver', 'playwright'])

    assert driver == 'playwright'
    assert restante == ['bot.py']


def test_driver_desconhecido_encerra_com_erro():
    with pytest.raises(SystemExit):
        separar_driver(['bot.py', '--driver', 'cypress'])


def test_help_encerra_sem_executar_nada():
    """
    Com add_help desligado, --help viraria argumento desconhecido e o robô
    executaria — abrindo navegador para quem só queria ler a ajuda.
    """
    with pytest.raises(SystemExit):
        separar_driver(['bot.py', '--help'])


def test_obter_driver_dos_argumentos_reescreve_o_sys_argv(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['bot.py', '--driver', 'selenium', *MAESTRO])

    driver = obter_driver_dos_argumentos()

    assert driver == 'selenium'
    assert sys.argv == ['bot.py', *MAESTRO]
