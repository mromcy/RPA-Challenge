"""
Construção do driver a partir do nome.

É o único lugar do projeto que conhece as duas implementações ao mesmo tempo.
O resto do código conhece apenas o contrato BrowserDriver.
"""

from resources.Drivers.base import BrowserDriver
from resources.settings import get_settings

DRIVERS_DISPONIVEIS = ('playwright', 'selenium')


def criar_driver(nome: str | None = None, headless: bool = True) -> BrowserDriver:
    """
    Devolve o driver pedido, já configurado a partir das configurações.

    Os imports das bibliotecas acontecem **dentro** de cada ramo, e não no topo
    do módulo, por dois motivos. Primeiro, uma execução só deve pagar o custo de
    importar a biblioteca que vai usar: `playwright.sync_api` carrega 177 módulos
    e `selenium.webdriver` carrega 23. Segundo, e mais importante: o benchmark
    mede o tempo de partida, e importar as duas em toda execução somaria o mesmo
    custo aos dois lados, escondendo a diferença real de startup.

    É por isso que as duas linhas de import carregam `noqa: PLC0415` — a regra
    está certa como padrão, e esta é a exceção que ela existe para permitir.

    Args:
        nome: 'playwright' ou 'selenium'. Omitido, usa Settings.DRIVER.
        headless: Sem janela visível.

    Returns:
        BrowserDriver: Implementação pronta para uso.

    Raises:
        ValueError: Se o nome não corresponder a nenhum driver conhecido.
    """
    settings = get_settings()
    escolhido = (nome or settings.DRIVER).strip().lower()

    if escolhido == 'playwright':
        from resources.Drivers.playwright_driver import (  # noqa: PLC0415
            PlaywrightDriver,
        )

        return PlaywrightDriver(
            headless=headless,
            path_browser=settings.PATH_BROWSER,
        )

    if escolhido == 'selenium':
        from resources.Drivers.selenium_driver import (  # noqa: PLC0415
            SeleniumDriver,
        )

        return SeleniumDriver(
            headless=headless,
            path_browser=settings.PATH_BROWSER,
            path_driver=settings.PATH_SELENIUM_DRIVER,
        )

    raise ValueError(
        f'Driver desconhecido: {escolhido!r}. '
        f'Disponíveis: {", ".join(DRIVERS_DISPONIVEIS)}.'
    )
