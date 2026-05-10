"""
1 - Classe com as funcionalidades do sistema que será automatizado.
2 - Responsável pelas interações com a página do RPA Challenge.
3 - Utiliza os localizadores definidos em locators.py.
"""

import time

import pandas as pd
from playwright.sync_api import Page

from resources.Modules.locators import LocatorChallenge


class Challenge:
    """Classe responsável pelas interações com a página do RPA Challenge."""

    def __init__(self, page: Page) -> None:
        """
        Inicializa a classe com a página do Playwright e resolve os localizadores.

        Args:
            page: Instância da página do Playwright já criada pelo browser.
        """
        self.page = page
        loc = LocatorChallenge

        # Resolve cada localizador uma única vez para reutilização nos métodos
        self.btn_start = loc.btn_start(page)
        self.btn_submit = loc.btn_submit(page)
        self.input_first_name = loc.input_first_name(page)
        self.input_last_name = loc.input_last_name(page)
        self.input_company_name = loc.input_company_name(page)
        self.input_role_in_company = loc.input_role_in_company(page)
        self.input_address = loc.input_address(page)
        self.input_email = loc.input_email(page)
        self.input_phone_number = loc.input_phone_number(page)

    def iniciar_desafio(self, url: str) -> None:
        """
        Navega para a URL do desafio e clica no botão 'Start'.

        Deve ser chamado uma única vez antes do preenchimento dos formulários.

        Args:
            url: URL do sistema a ser acessado, proveniente das configurações.
        """
        # Navega para a página inicial do desafio
        self.page.goto(url)
        self.btn_start.click()

    def preencher_formulario(self, row: pd.Series) -> None:
        """
        Preenche todos os campos do formulário com os dados de uma linha da planilha
        e clica em 'Submit'.

        Args:
            row: Linha do DataFrame pandas contendo os dados do registro atual.
                 Espera as colunas: 'First Name', 'Last Name', 'Company Name',
                 'Role in Company', 'Address', 'Email', 'Phone Number'.
        """
        # Preenche cada campo do formulário com o valor correspondente da linha
        self.input_first_name.fill(str(row['First Name']))
        self.input_last_name.fill(str(row['Last Name']))
        self.input_company_name.fill(str(row['Company Name']))
        self.input_role_in_company.fill(str(row['Role in Company']))
        self.input_address.fill(str(row['Address']))
        self.input_email.fill(str(row['Email']))
        self.input_phone_number.fill(str(row['Phone Number']))

        # Envia o formulário após preencher todos os campos
        self.btn_submit.click()

    def aguardar_resultado(self, segundos: int = 5) -> None:
        """
        Aguarda após o envio do último formulário para que o resultado
        final do desafio seja exibido na tela antes de fechar o navegador.

        Args:
            segundos: Tempo de espera em segundos. Padrão: 5.
        """
        # Aguarda para visualização do resultado final antes do encerramento
        time.sleep(segundos)
