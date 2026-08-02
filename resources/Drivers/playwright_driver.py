"""
Implementação do BrowserDriver sobre o Playwright.

Todo o conhecimento de Playwright do projeto fica confinado aqui: fora deste
arquivo ninguém importa `playwright`, e por isso o fluxo de negócio pode ser
testado sem navegador.
"""

from typing import Any

from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from resources.Drivers import seletores
from resources.Drivers.base import TIMEOUT_PADRAO_MS


class PlaywrightDriver:
    """
    Dirige o RPA Challenge com o Playwright.

    Não herda de BrowserDriver: a conformidade com o Protocol é estrutural.

    O navegador só sobe na primeira chamada a abrir(), e não no __init__, para
    que construir o driver seja barato e não deixe processo pendurado se algo
    falhar antes do uso.
    """

    nome = 'playwright'

    def __init__(self, headless: bool = True, path_browser: str = ''):
        """
        Args:
            headless: Sem janela visível. Padrão do robô e do benchmark.
            path_browser: Executável do navegador. Vazio significa usar o
                Chromium que o próprio Playwright gerencia — ver decisão 10 do
                progresso. Não é lido das configurações aqui de propósito: quem
                monta o driver é que decide, o que mantém a classe testável.
        """
        self._headless = headless
        self._path_browser = path_browser
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    @property
    def _pagina(self) -> Page:
        """
        Página ativa, com erro explícito se o driver não foi aberto.

        Sem isso, usar o driver fora de ordem produziria um AttributeError em
        None, que não diz o que fazer.
        """
        if self._page is None:
            raise RuntimeError(
                'Driver do Playwright não iniciado: chame abrir(url) antes.'
            )
        return self._page

    def abrir(self, url: str) -> None:
        """Sobe o navegador na primeira chamada e navega até a URL."""
        if self._page is None:
            self._playwright = sync_playwright().start()

            # Argumento omitido — e não vazio — quando não há executável
            # apontado: string vazia faria o Playwright tentar executá-la.
            extras: dict[str, Any] = {}
            if self._path_browser:
                extras['executable_path'] = self._path_browser

            if not self._headless:
                # Execução acompanhada pelo operador: janela ocupando a tela,
                # como no comportamento anterior ao driver.
                extras['args'] = ['--start-maximized']

            self._browser = self._playwright.chromium.launch(
                headless=self._headless, **extras
            )
            self._page = self._browser.new_page(no_viewport=not self._headless)

        self._pagina.goto(url, timeout=TIMEOUT_PADRAO_MS)

    def clicar_iniciar(self) -> None:
        """Clica em 'Start'."""
        self._pagina.locator(seletores.XPATH_BOTAO_INICIAR).click(
            timeout=TIMEOUT_PADRAO_MS
        )

    def preencher_campo(self, rotulo: str, valor: str) -> None:
        """Preenche o campo cujo rótulo visível é `rotulo`."""
        seletor = seletores.XPATH_CAMPO_POR_ROTULO.format(rotulo=rotulo)
        self._pagina.locator(seletor).fill(valor, timeout=TIMEOUT_PADRAO_MS)

    def enviar(self) -> None:
        """Clica em 'Submit'."""
        self._pagina.locator(seletores.XPATH_BOTAO_ENVIAR).click(
            timeout=TIMEOUT_PADRAO_MS
        )

    def ler_resultado(self) -> str:
        """
        Espera a mensagem final ficar visível e devolve o texto.

        A espera é explícita porque o contrato promete `str`: ler antes de o
        site renderizar devolveria vazio, que era a fonte de instabilidade do
        capturar_resultado anterior.
        """
        localizador = self._pagina.locator(seletores.XPATH_RESULTADO).first
        localizador.wait_for(state='visible', timeout=TIMEOUT_PADRAO_MS)
        return localizador.inner_text()

    def fechar(self) -> None:
        """
        Encerra navegador e Playwright, em qualquer estado.

        Cada etapa é independente: uma falha ao fechar o navegador não pode
        impedir o encerramento do Playwright, que é quem mantém o processo do
        driver vivo. Idempotente — chamar duas vezes não quebra.
        """
        try:
            if self._browser is not None:
                self._browser.close()
        finally:
            self._browser = None
            self._page = None

            if self._playwright is not None:
                self._playwright.stop()
                self._playwright = None
