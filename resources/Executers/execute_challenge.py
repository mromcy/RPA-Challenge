"""
1 - Executa as funcionalidades do sistema automatizado.
2 - Responsável pela orquestração do fluxo do RPA Challenge.
3 - Gerencia o ciclo de vida do navegador e a leitura da planilha.
"""

from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

from resources.Modules.challenge import Challenge
from resources.settings import Settings


def carregar_planilha(caminho: str) -> pd.DataFrame:
    """
    Carrega a planilha de dados do desafio a partir do caminho informado.

    Args:
        caminho: Caminho completo para o arquivo .xlsx.

    Returns:
        DataFrame pandas com os dados da planilha.
    """
    # Lê o arquivo Excel e retorna o DataFrame com todos os registros
    return pd.read_excel(caminho)


def executar_challenge() -> None:
    """
    Orquestra a execução completa do RPA Challenge.

    Fluxo:
        1. Carrega as configurações do config.json.
        2. Carrega os dados da planilha da pasta de entrada.
        3. Inicia o navegador Playwright.
        4. Instancia o Challenge e navega para a URL do desafio.
        5. Itera sobre cada linha da planilha e preenche o formulário.
        6. Aguarda a exibição do resultado final.
        7. Fecha o navegador.
    """
    settings = Settings()  # pyright: ignore[reportCallIssue]

    # Busca o primeiro .xlsx encontrado na pasta de entrada — independente do nome do arquivo
    arquivos = list(Path(settings.PATH_IN).glob('*.xlsx'))
    if not arquivos:
        raise FileNotFoundError(f'Nenhum arquivo .xlsx encontrado em: {settings.PATH_IN}')
    caminho_planilha = str(arquivos[0])

    # Carrega os dados antes de abrir o navegador — falha cedo se o arquivo estiver corrompido
    dados = carregar_planilha(caminho_planilha)

    with sync_playwright() as p:
        # Inicializa o navegador em modo visível com janela maximizada
        browser = p.chromium.launch(headless=False, args=['--start-maximized'])
        page = browser.new_page(no_viewport=True)

        challenge = Challenge(page)

        # Navega para a URL configurada e inicia o desafio
        challenge.iniciar_desafio(settings.PATH_URL)

        # Itera sobre cada linha da planilha e preenche o formulário correspondente
        for _, row in dados.iterrows():
            challenge.preencher_formulario(row)

        # Aguarda o resultado final antes de encerrar
        challenge.aguardar_resultado()

        browser.close()
