"""
Implementação do BrowserDriver sobre o Selenium WebDriver.

Todo o conhecimento de Selenium do projeto fica confinado aqui, como o de
Playwright fica em playwright_driver.py. Os dois usam os mesmos seletores e o
mesmo tempo-limite, para que a comparação do benchmark meça a biblioteca e não
a qualidade do código de cada lado.
"""

from collections.abc import Callable
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from resources.Drivers import seletores
from resources.Drivers.base import TIMEOUT_PADRAO_MS


class SeleniumDriver:
    """
    Dirige o RPA Challenge com o Selenium WebDriver.

    Não herda de BrowserDriver: a conformidade com o Protocol é estrutural.

    O navegador só sobe na primeira chamada a abrir(), e não no __init__, para
    que construir o driver seja barato e não deixe processo pendurado se algo
    falhar antes do uso.
    """

    nome = 'selenium'

    def __init__(
        self,
        headless: bool = True,
        path_browser: str = '',
        path_driver: str = '',
    ):
        """
        Args:
            headless: Sem janela visível. Padrão do robô e do benchmark.
            path_browser: Executável do navegador. Vazio significa deixar o
                Selenium usar o Chrome instalado no sistema — ver decisão 10 do
                progresso. Não é lido das configurações aqui de propósito: quem
                monta o driver é que decide, o que mantém a classe testável.
            path_driver: Executável do chromedriver. Vazio significa deixar o
                Selenium Manager baixar a versão correspondente ao navegador.
                Só é necessário em máquina sem saída para a internet.
        """
        self._headless = headless
        self._path_browser = path_browser
        self._path_driver = path_driver
        self._navegador: webdriver.Chrome | None = None

    @property
    def _navegador_ativo(self) -> webdriver.Chrome:
        """
        Navegador em uso, com erro explícito se o driver não foi aberto.

        Sem isso, usar o driver fora de ordem produziria um AttributeError em
        None, que não diz o que fazer.
        """
        if self._navegador is None:
            raise RuntimeError(
                'Driver do Selenium não iniciado: chame abrir(url) antes.'
            )
        return self._navegador

    def _esperar(
        self,
        condicao: Callable[[tuple[str, str]], Any],
        seletor: str,
    ) -> WebElement:
        """
        Espera uma condição valer para o seletor e devolve o elemento.

        **O que este auxiliar faz, passo a passo:**

        1. Monta o localizador no formato que o Selenium espera — a tupla
           ``(By.XPATH, seletor)``.
        2. Cria um ``WebDriverWait`` com o tempo-limite compartilhado do
           projeto. O ``TIMEOUT_PADRAO_MS`` está em milissegundos, porque é a
           unidade do Playwright; o Selenium recebe segundos, então a conversão
           acontece aqui. Existe um único número na base de código, e é ele que
           os dois drivers honram.
        3. Chama ``.until(condicao(localizador))``, que **repete a consulta ao
           DOM** — por padrão a cada 0,5 s — até a condição ser satisfeita ou o
           tempo esgotar. Enquanto isso, engole as exceções que o Selenium
           levanta quando o elemento ainda não existe, em vez de deixá-las
           subir.
        4. Devolve o WebElement já pronto para receber a ação.
        5. Se o tempo esgotar, deixa o ``TimeoutException`` subir, com a
           mensagem indicando qual espera falhou.

        **Por que ele existe:** no Playwright, `locator.click()` já executa
        essas verificações sozinho antes de agir. No Selenium não existe
        equivalente embutido, e sem um auxiliar como este cada método do driver
        repetiria as mesmas quatro linhas. A camada de espera que o Playwright
        entrega pronta é, aqui, código que alguém precisa escrever e manter —
        e esse é justamente um dos custos que o benchmark quer tornar visível.

        **O que ele NÃO faz, e a comparação precisa declarar:** as condições
        prontas do Selenium cobrem menos que a verificação do Playwright. O
        ``element_to_be_clickable`` garante *presente*, *visível* e
        *habilitado*, mas não garante *estável* (elemento parado, sem animação)
        nem *desobstruído* (nada por cima interceptando o clique). Reproduzir
        essas duas exigiria condições customizadas. A paridade entre os drivers
        é, portanto, aproximada — e é aqui que ela fica devendo.

        Args:
            condicao: Fábrica de condição do módulo expected_conditions, por
                exemplo ``EC.element_to_be_clickable``.
            seletor: XPath do elemento, vindo de Drivers/seletores.py.

        Returns:
            WebElement: Elemento que satisfez a condição.

        Raises:
            TimeoutException: Se a condição não valer dentro do tempo-limite.
        """
        espera = WebDriverWait(self._navegador_ativo, TIMEOUT_PADRAO_MS / 1000)
        return espera.until(condicao((By.XPATH, seletor)))

    def abrir(self, url: str) -> None:
        """Sobe o navegador na primeira chamada e navega até a URL."""
        if self._navegador is None:
            opcoes = Options()

            if self._headless:
                # --headless=new é o modo headless moderno do Chrome; o antigo
                # tinha diferenças de comportamento que geravam falha só em CI.
                opcoes.add_argument('--headless=new')
            else:
                # Execução acompanhada pelo operador: janela ocupando a tela.
                opcoes.add_argument('--start-maximized')

            if self._path_browser:
                opcoes.binary_location = self._path_browser

            # Service omitido — e não vazio — quando não há chromedriver
            # apontado: aí o Selenium Manager resolve a versão correspondente.
            servico = None
            if self._path_driver:
                servico = Service(executable_path=self._path_driver)

            self._navegador = webdriver.Chrome(options=opcoes, service=servico)
            self._navegador.set_page_load_timeout(TIMEOUT_PADRAO_MS / 1000)

        self._navegador_ativo.get(url)

    def clicar_iniciar(self) -> None:
        """Clica em 'Start'."""
        self._esperar(
            EC.element_to_be_clickable, seletores.XPATH_BOTAO_INICIAR
        ).click()

    def preencher_campo(self, rotulo: str, valor: str) -> None:
        """
        Preenche o campo cujo rótulo visível é `rotulo`.

        O clear() antes do send_keys reproduz o comportamento do fill() do
        Playwright, que substitui o conteúdo em vez de acrescentar ao que já
        estiver lá.
        """
        seletor = seletores.XPATH_CAMPO_POR_ROTULO.format(rotulo=rotulo)
        campo = self._esperar(EC.element_to_be_clickable, seletor)
        campo.clear()
        campo.send_keys(valor)

    def enviar(self) -> None:
        """Clica em 'Submit'."""
        self._esperar(
            EC.element_to_be_clickable, seletores.XPATH_BOTAO_ENVIAR
        ).click()

    def ler_resultado(self) -> str:
        """
        Espera a mensagem final ficar visível e devolve o texto.

        A espera é explícita porque o contrato promete `str`: ler antes de o
        site renderizar devolveria vazio.
        """
        return self._esperar(
            EC.visibility_of_element_located, seletores.XPATH_RESULTADO
        ).text

    def fechar(self) -> None:
        """
        Encerra o navegador e o processo do chromedriver.

        O quit() derruba os dois; o close() fecharia apenas a janela, deixando
        o processo do driver vivo. Idempotente — chamar duas vezes não quebra.
        """
        try:
            if self._navegador is not None:
                self._navegador.quit()
        finally:
            self._navegador = None
