"""
Testes do fluxo de negócio (resources/Modules/challenge.py).

Rodam sem navegador: o Challenge fala com um BrowserDriver, e nos testes esse
driver é o FakeDriver, que apenas registra o que foi pedido. É o ganho que
justifica a inversão de dependência do P2 — antes deste bloco, challenge.py
tinha 0% de cobertura porque não havia como exercitá-lo sem subir um browser.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from resources.Modules.challenge import CAMPOS_DO_FORMULARIO, Challenge
from resources.Schemas.item_run import Item
from tests.fake_driver import RESULTADO_PADRAO, FakeDriver

URL = 'https://rpachallenge.com/'


def _item(**sobrescritas) -> Item:
    """Item com os sete campos preenchidos, sobrescrevíveis por nome."""
    valores = {
        'id': 1,
        'item_id': 1,
        'First_Name': 'Marco',
        'Last_Name': 'Romcy',
        'Company_Name': 'Empresa Ficticia',
        'Role_in_Company': 'RPA Developer',
        'Address': 'Rua de Teste, 123',
        'Email': 'teste@exemplo.invalido',
        'Phone_Number': '5511999999999',
    }
    return Item(**{**valores, **sobrescritas})


@pytest.fixture
def driver():
    return FakeDriver()


@pytest.fixture
def challenge(driver):
    return Challenge(driver, MagicMock())


def test_iniciar_desafio_navega_e_depois_clica_em_start(challenge, driver):
    challenge.iniciar_desafio(URL)

    assert driver.chamadas == [('abrir', URL), ('clicar_iniciar',)]


def test_preencher_formulario_preenche_os_sete_campos(challenge, driver):
    challenge.preencher_formulario(_item())

    assert driver.campos_preenchidos == {
        'First Name': 'Marco',
        'Last Name': 'Romcy',
        'Company Name': 'Empresa Ficticia',
        'Role in Company': 'RPA Developer',
        'Address': 'Rua de Teste, 123',
        'Email': 'teste@exemplo.invalido',
        'Phone Number': '5511999999999',
    }


def test_preencher_formulario_envia_depois_de_preencher_tudo(challenge, driver):
    """O envio precisa ser a última operação: enviar no meio perde campos."""
    challenge.preencher_formulario(_item())

    preenchimentos = ['preencher_campo'] * len(CAMPOS_DO_FORMULARIO)
    assert driver.operacoes == [*preenchimentos, 'enviar']


def test_preencher_formulario_envia_uma_vez_por_item(challenge, driver):
    itens = [_item(First_Name='Ana'), _item(First_Name='Bruno')]

    for item in itens:
        challenge.preencher_formulario(item)

    assert driver.operacoes.count('enviar') == len(itens)


def test_preencher_formulario_usa_os_valores_do_item_recebido(challenge, driver):
    challenge.preencher_formulario(_item(First_Name='Ana', Email='ana@exemplo.invalido'))

    assert driver.campos_preenchidos['First Name'] == 'Ana'
    assert driver.campos_preenchidos['Email'] == 'ana@exemplo.invalido'


def test_capturar_resultado_devolve_o_texto_lido_pelo_driver(challenge):
    assert challenge.capturar_resultado() == RESULTADO_PADRAO


def test_capturar_resultado_nao_devolve_none():
    """
    O contrato promete str. O capturar_resultado anterior devolvia str | None
    porque lia sem esperar — esta trava impede a volta do None.
    """
    challenge = Challenge(FakeDriver(resultado=''), MagicMock())

    assert isinstance(challenge.capturar_resultado(), str)


def test_mapa_de_campos_cobre_todos_os_campos_de_formulario_do_item():
    """
    Trava de sincronia: se alguém acrescentar um campo de formulário ao Item e
    esquecer do mapa, o robô passaria a enviar o formulário incompleto sem erro
    nenhum — o site simplesmente pontuaria menos.
    """
    nao_sao_campos_de_formulario = {'id', 'item_id', 'result'}
    campos_do_item = set(Item.model_fields) - nao_sao_campos_de_formulario

    assert set(CAMPOS_DO_FORMULARIO.values()) == campos_do_item


def test_fluxo_de_negocio_nao_depende_de_biblioteca_de_navegador():
    """
    Trava de arquitetura do P2: importar o fluxo não pode carregar Playwright
    nem Selenium. Roda em subprocesso porque, no processo do pytest, outro
    teste pode já ter importado a biblioteca por outro caminho.
    """
    codigo = (
        'import sys; import resources.Modules.challenge; '
        "print([m for m in sys.modules if 'playwright' in m or 'selenium' in m])"
    )
    resultado = subprocess.run(
        [sys.executable, '-c', codigo],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    )

    assert resultado.stdout.strip() == '[]'
