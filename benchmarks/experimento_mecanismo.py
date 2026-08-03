"""
Experimento: de onde vem a diferença de tempo entre Playwright e Selenium?

O benchmark mostra o Playwright ~6,7× mais rápido na fase de preenchimento.
Este script existe para responder **por quê**, separando duas explicações que o
número sozinho não distingue:

1. **Custo da espera** — cada interação do Selenium passa por um WebDriverWait,
   que consulta o DOM em intervalos até a condição valer.
2. **Custo por comando** — o Selenium fala com o navegador por HTTP com o
   chromedriver, uma requisição e uma resposta por comando, enquanto o
   Playwright mantém um WebSocket persistente. E o Selenium gasta três comandos
   por campo (localizar, clear, send_keys) contra um do Playwright.

O método é isolar uma variável por vez, herdando do driver de produção e
sobrescrevendo o mínimo:

- `SeleniumSemEspera` troca o WebDriverWait por find_element direto. Se o tempo
  não mudar, a espera **não** é o gargalo.
- `SeleniumSemEsperaSemClear` remove também o clear(), caindo de três comandos
  por campo para dois. Se o tempo cair perto de um terço, o custo é por comando.

**Estas variantes não são código de produção.** Sem espera explícita, o driver
volta a ser suscetível a corrida — é exatamente a robustez que o driver real
compra com os statements a mais.

    poetry run python -m benchmarks.experimento_mecanismo --repeticoes 3
"""

from __future__ import annotations

import argparse
import statistics

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from benchmarks import compare_drivers
from benchmarks.compare_drivers import (
    carregar_itens,
    uma_execucao,
    versao_do_navegador,
)
from resources.Drivers import seletores
from resources.Drivers.playwright_driver import PlaywrightDriver
from resources.Drivers.selenium_driver import SeleniumDriver
from resources.Modules.challenge import CAMPOS_DO_FORMULARIO
from resources.settings import get_settings


class SeleniumSemEspera(SeleniumDriver):
    """Selenium com find_element direto, sem WebDriverWait. Isola a espera."""

    nome = 'selenium-sem-espera'

    def _esperar(self, condicao, seletor: str) -> WebElement:  # noqa: ARG002
        return self._navegador_ativo.find_element(By.XPATH, seletor)


class SeleniumSemEsperaSemClear(SeleniumSemEspera):
    """Também sem o clear(): dois comandos por campo em vez de três."""

    nome = 'selenium-sem-espera-sem-clear'

    def preencher_campo(self, rotulo: str, valor: str) -> None:
        seletor = seletores.XPATH_CAMPO_POR_ROTULO.format(rotulo=rotulo)
        self._esperar(None, seletor).send_keys(valor)


VARIANTES = {
    'playwright': PlaywrightDriver,
    'selenium': SeleniumDriver,
    'selenium-sem-espera': SeleniumSemEspera,
    'selenium-sem-espera-sem-clear': SeleniumSemEsperaSemClear,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='experimento_mecanismo',
        description='Separa custo de espera de custo de comando no Selenium.',
    )
    parser.add_argument('--repeticoes', type=int, default=3)
    argumentos = parser.parse_args()

    path_browser = get_settings().PATH_BROWSER
    if not path_browser:
        raise SystemExit(
            'PATH_BROWSER está vazio: as variantes precisam do mesmo Chrome.'
        )

    itens = carregar_itens()

    # 7 campos por item, mais um envio por item, mais o clique inicial no Start.
    interacoes = len(itens) * len(CAMPOS_DO_FORMULARIO) + len(itens) + 1

    print(f'Navegador: Chrome {versao_do_navegador(path_browser)}')
    print(f'Interações com a página por execução: {interacoes}')

    # O uma_execucao() do benchmark consulta CONSTRUTORES pelo nome; aqui as
    # variantes são outras, então o mapa é substituído em memória.
    compare_drivers.CONSTRUTORES = VARIANTES

    medicoes: dict[str, list[float]] = {nome: [] for nome in VARIANTES}

    print('\nAquecimento (descartado)...')
    for nome in VARIANTES:
        uma_execucao(nome, itens, path_browser)
        print(f'  {nome}: ok')

    print(f'\nMedindo {argumentos.repeticoes} execuções por variante, intercaladas...')
    for rodada in range(1, argumentos.repeticoes + 1):
        for nome in VARIANTES:
            tempos = uma_execucao(nome, itens, path_browser)
            medicoes[nome].append(tempos['fill'])
            print(f'  rodada {rodada} · {nome:<32} fill={tempos["fill"]:5.2f}s')

    print('\n### Tempo de preenchimento por variante\n')
    print('| Variante | fill mediano (s) | vs. Selenium |')
    print('|---|---|---|')

    base = statistics.median(medicoes['selenium'])
    for nome, valores in medicoes.items():
        mediana = statistics.median(valores)
        print(f'| {nome} | {mediana:.2f} | {mediana / base:.2f}× |')


if __name__ == '__main__':
    main()
