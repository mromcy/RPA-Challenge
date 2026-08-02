"""
Testes de ponta a ponta contra o rpachallenge.com ao vivo.

Uma suíte só, dois backends de navegador, o mesmo assert — é literalmente o que
se faz em teste cross-browser.

Ficam fora do lane rápido pelo marker `e2e`, porque dependem de sistema externo:
o site pode sair do ar, mudar o DOM ou oscilar de rede. Falha aqui nem sempre
significa defeito no código, e CI vermelho por motivo alheio ensina o time a
ignorar o vermelho.

Os drivers são construídos **diretamente**, e não pela fábrica: a fábrica
aplicaria o PATH_BROWSER do config.json, e com ele preenchido os dois drivers
passariam a usar o mesmo navegador — exatamente a cobertura cross-browser que
estes testes existem para dar (decisão 12 do progresso). Como efeito colateral
útil, a suíte roda sem config.json algum.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from resources.Drivers.playwright_driver import PlaywrightDriver
from resources.Drivers.selenium_driver import SeleniumDriver
from resources.Modules.challenge import CAMPOS_DO_FORMULARIO, Challenge
from resources.Schemas.item_run import Item
from resources.Utils.ler_arquivo import LerArquivo

URL = 'https://rpachallenge.com/'
PASTA_DE_ENTRADA = Path(__file__).resolve().parents[1] / 'Entrada'

CONSTRUTORES = {
    'playwright': PlaywrightDriver,
    'selenium': SeleniumDriver,
}


@pytest.fixture
def driver(request):
    """
    Instancia o driver pedido em headless e garante fechar() no teardown.

    O que vem depois do yield roda mesmo quando o teste falha, o que impede um
    navegador ficar pendurado na memória quando o site muda ou cai.
    """
    instancia = CONSTRUTORES[request.param](headless=True)

    yield instancia

    instancia.fechar()


@pytest.fixture(scope='module')
def itens() -> list[Item]:
    """
    Os dez registros de Entrada/challenge.xlsx, no formato que o fluxo consome.

    Reaproveita LerArquivo e limpar_dataframe em vez de reimplementar a leitura:
    é o mesmo caminho que a produção percorre, então uma quebra ali aparece
    aqui também. Escopo de módulo porque o arquivo não muda entre os testes.
    """
    dados = LerArquivo(MagicMock(), path_in=PASTA_DE_ENTRADA).ler_arquivo()

    return [
        Item(
            id=numero,
            item_id=numero,
            **{
                atributo: str(linha[rotulo])
                for rotulo, atributo in CAMPOS_DO_FORMULARIO.items()
            },
        )
        for numero, (_, linha) in enumerate(dados.iterrows(), 1)
    ]


@pytest.mark.e2e
@pytest.mark.parametrize('driver', CONSTRUTORES, indirect=True)
def test_desafio_completo_com_sucesso_total(driver, itens):
    """
    O fluxo inteiro, do zero ao resultado, no navegador de verdade.

    O `indirect=True` faz o valor do parametrize chegar à fixture `driver` em
    vez de ao teste: cada nome vira uma instância diferente, e o corpo do teste
    não sabe qual biblioteca está do outro lado — que é a prova de que a
    abstração funciona.
    """
    challenge = Challenge(driver, MagicMock())

    challenge.iniciar_desafio(URL)
    for item in itens:
        challenge.preencher_formulario(item)

    resultado = challenge.capturar_resultado()

    assert '100%' in resultado, f'Driver {driver.nome} não zerou o desafio: {resultado}'
    assert '70 out of 70' in resultado
