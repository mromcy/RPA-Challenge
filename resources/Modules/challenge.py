"""
1 - Classe com as funcionalidades do sistema que será automatizado.
2 - Responsável pelas interações com a página do RPA Challenge.
3 - Utiliza os localizadores definidos em locators.py.
"""

import time

from playwright.sync_api import Page

from resources.Modules.locators import LocatorChallenge
from resources.Schemas.item_run import Item
from resources.Tools.logs import Logs


class Challenge:
    """Classe responsável pelas interações com a página do RPA Challenge."""

    def __init__(self, page: Page, logs: Logs) -> None:
        """
        Inicializa a classe com a página do Playwright e resolve os localizadores.

        Args:
            page: Instância da página do Playwright já criada pelo browser.
            logs: Instância de Logs para registro das operações.
        """
        self.page = page
        self.logs = logs
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
        self.resultado_final = loc.resultado_final(page)

    def iniciar_desafio(self, url: str) -> None:
        """
        Navega para a URL do desafio e clica no botão 'Start'.

        Deve ser chamado uma única vez antes do preenchimento dos formulários.

        Args:
            url: URL do sistema a ser acessado, proveniente das configurações.
        """
        self.logs.info("Navegando para a URL do RPA Challenge.")
        self.page.goto(url)
        self.btn_start.click()
        self.logs.info("Desafio iniciado com sucesso.")

    def preencher_formulario(self, item: Item) -> None:
        """
        Preenche todos os campos do formulário com os dados do item lido do banco
        e clica em 'Submit'.

        Args:
            item: Schema Pydantic com os dados do registro atual,
                  lido da tabela item via get_queued_items_by_run.
        """
        self.logs.info(f'Preenchendo formulário: {item.First_Name} {item.Last_Name}.')
        self.input_first_name.fill(item.First_Name)
        self.input_last_name.fill(item.Last_Name)
        self.input_company_name.fill(item.Company_Name)
        self.input_role_in_company.fill(item.Role_in_Company)
        self.input_address.fill(item.Address)
        self.input_email.fill(item.Email)
        self.input_phone_number.fill(item.Phone_Number)

        # Envia o formulário após preencher todos os campos
        self.btn_submit.click()

    def capturar_resultado(self):
        """
        Aguarda após o envio do último formulário para que o resultado
        final do desafio seja exibido e capturado antes de fechar o navegador.

        Args:
            segundos: Tempo de espera em segundos. Padrão: 5.
        """
        resultado = self.resultado_final.text_content()
        self.logs.info(resultado)
        
        return resultado
