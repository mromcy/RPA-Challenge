"""
Testes de resources/Drivers/factory.py.

A leitura do parâmetro de task vive na fábrica, e não no execute.py, porque
aquele módulo abre conexão com o banco em tempo de import — a regra ficaria
fora do alcance da suíte unitária.
"""

import pytest

from resources.Drivers.factory import (
    DRIVERS_DISPONIVEIS,
    driver_dos_parametros,
    resolver_driver,
)


def test_sem_parametros_devolve_none():
    """Modo local: o BotExecution vem com parameters vazio."""
    assert driver_dos_parametros({}) is None


def test_parametro_ausente_devolve_none():
    assert driver_dos_parametros({'outra_coisa': 'valor'}) is None


def test_parametro_vazio_devolve_none():
    """Campo deixado em branco no painel não deve sobrepor o padrão."""
    assert driver_dos_parametros({'driver': ''}) is None


@pytest.mark.parametrize('nome', DRIVERS_DISPONIVEIS)
def test_devolve_cada_driver_disponivel(nome):
    assert driver_dos_parametros({'driver': nome}) == nome


def test_normaliza_espacos_e_maiusculas():
    """Valor digitado à mão no painel do Maestro costuma vir sujo."""
    assert driver_dos_parametros({'driver': '  SELENIUM '}) == 'selenium'


def test_linha_de_comando_vence_o_parametro_da_task():
    """
    A camada mais específica ganha: quem digitou a flag agora quis aquilo agora,
    mesmo que a task tenha sido criada pedindo outra coisa.
    """
    assert resolver_driver('playwright', {'driver': 'selenium'}) == 'playwright'


def test_sem_linha_de_comando_vale_o_parametro_da_task():
    assert resolver_driver(None, {'driver': 'selenium'}) == 'selenium'


def test_sem_nenhum_dos_dois_devolve_none():
    """None significa "decida pelo config.json" — a camada mais geral."""
    assert resolver_driver(None, {}) is None


def test_resolucao_rejeita_parametro_invalido_da_task():
    with pytest.raises(ValueError, match='playwright, selenium'):
        resolver_driver(None, {'driver': 'cypress'})


def test_driver_desconhecido_levanta_erro_citando_os_validos():
    """
    Falha na partida, antes de as migrações rodarem e de a execução ser
    registrada no banco — um erro de digitação no painel não deve deixar
    rastro de execução falhada.
    """
    with pytest.raises(ValueError, match='playwright, selenium'):
        driver_dos_parametros({'driver': 'cypress'})
