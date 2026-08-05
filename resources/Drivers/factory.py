"""
Construção do driver a partir do nome.

É o único lugar do projeto que conhece as duas implementações ao mesmo tempo.
O resto do código conhece apenas o contrato BrowserDriver.
"""

from collections.abc import Mapping

from resources.Drivers.base import BrowserDriver
from resources.settings import get_settings

DRIVERS_DISPONIVEIS = ('playwright', 'selenium')


def driver_dos_parametros(parametros: Mapping[str, object]) -> str | None:
    """
    Lê o driver dos parâmetros de uma task do BotCity Maestro.

    Permite escolher a biblioteca ao disparar a task pelo painel, sem redeploy
    e sem registrar uma segunda automação. Fica aqui, e não no execute.py,
    porque aquele módulo não pode ser importado sem banco — a regra ficaria
    fora do alcance da suíte unitária.

    Args:
        parametros: Dicionário de parâmetros da execução. Vazio em modo local.

    Returns:
        str | None: Nome do driver, ou None quando o parâmetro não foi
            informado — caso em que a decisão volta para Settings.DRIVER.

    Raises:
        ValueError: Se o parâmetro trouxer um driver desconhecido. Falha aqui,
            na partida, é melhor que falhar depois de as migrações rodarem e o
            registro da execução já existir no banco.
    """
    valor = parametros.get('driver')
    if not valor:
        return None

    nome = str(valor).strip().lower()
    if nome not in DRIVERS_DISPONIVEIS:
        raise ValueError(
            f'Parâmetro "driver" da task com valor desconhecido: {valor!r}. '
            f'Disponíveis: {", ".join(DRIVERS_DISPONIVEIS)}.'
        )

    return nome


def resolver_driver(
    da_linha_de_comando: str | None,
    parametros_da_task: Mapping[str, object],
) -> str | None:
    """
    Decide o driver em três camadas, da mais específica para a mais geral.

    1. `--driver` na linha de comando: quem digitou agora quis isto agora.
    2. Parâmetro `driver` da task do Maestro: escolha para *esta* execução,
       feita no painel, sem redeploy.
    3. `None`, deixando `criar_driver` cair no `DRIVER` do config.json, que é o
       padrão da máquina.

    Args:
        da_linha_de_comando: Valor de `--driver`, se informado.
        parametros_da_task: Parâmetros da execução. Vazio em modo local.

    Returns:
        str | None: Driver escolhido, ou None para usar o padrão da máquina.

    Raises:
        ValueError: Se o parâmetro da task trouxer um driver desconhecido.
    """
    return da_linha_de_comando or driver_dos_parametros(parametros_da_task)


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
