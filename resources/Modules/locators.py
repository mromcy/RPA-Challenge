"""
1 - Classe com os seletores da tela do sistema que será automatizado.
2 - Contém todos os localizadores da página do RPA Challenge.
3 - Nenhuma lógica de negócio deve ser adicionada aqui.
"""

from playwright.sync_api import Locator, Page


class LocatorChallenge:
    """Centraliza todos os localizadores de elementos da página do RPA Challenge."""

    @staticmethod
    def btn_start(page: Page) -> Locator:
        """Retorna o botão 'Start' da página inicial do desafio."""
        return page.get_by_role('button', name='Start')

    @staticmethod
    def btn_submit(page: Page) -> Locator:
        """Retorna o botão 'Submit' para envio do formulário."""
        return page.get_by_role('button', name='Submit')

    @staticmethod
    def input_first_name(page: Page) -> Locator:
        """Retorna o campo de entrada 'First Name' do formulário."""
        return page.locator("//label[text()='First Name']/following-sibling::input")

    @staticmethod
    def input_last_name(page: Page) -> Locator:
        """Retorna o campo de entrada 'Last Name' do formulário."""
        return page.locator("//label[text()='Last Name']/following-sibling::input")

    @staticmethod
    def input_company_name(page: Page) -> Locator:
        """Retorna o campo de entrada 'Company Name' do formulário."""
        return page.locator("//label[text()='Company Name']/following-sibling::input")

    @staticmethod
    def input_role_in_company(page: Page) -> Locator:
        """Retorna o campo de entrada 'Role in Company' do formulário."""
        return page.locator("//label[text()='Role in Company']/following-sibling::input")

    @staticmethod
    def input_address(page: Page) -> Locator:
        """Retorna o campo de entrada 'Address' do formulário."""
        return page.locator("//label[text()='Address']/following-sibling::input")

    @staticmethod
    def input_email(page: Page) -> Locator:
        """Retorna o campo de entrada 'Email' do formulário."""
        return page.locator("//label[text()='Email']/following-sibling::input")

    @staticmethod
    def input_phone_number(page: Page) -> Locator:
        """Retorna o campo de entrada 'Phone Number' do formulário."""
        return page.locator("//label[text()='Phone Number']/following-sibling::input")
