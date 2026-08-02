"""
1 - Fluxo de negócio do RPA Challenge.
2 - Fala com o navegador exclusivamente pelo contrato BrowserDriver.
3 - Não importa Playwright nem Selenium: qual biblioteca dirige a tela é
    decisão de quem monta o driver, e este módulo não precisa saber.
"""

from resources.Drivers.base import BrowserDriver
from resources.Schemas.item_run import Item
from resources.Tools.logs import Logs

CAMPOS_DO_FORMULARIO = {
    'First Name': 'First_Name',
    'Last Name': 'Last_Name',
    'Company Name': 'Company_Name',
    'Role in Company': 'Role_in_Company',
    'Address': 'Address',
    'Email': 'Email',
    'Phone Number': 'Phone_Number',
}
"""
Rótulo exibido na tela → atributo correspondente em Item.

Mapa de dados, e não sete chamadas escritas à mão: acrescentar um campo ao
formulário passa a ser uma linha aqui, sem tocar em nenhum driver. Os rótulos
são os que o desafio realmente exibe, e é por eles que os campos são
localizados — o site embaralha a ordem a cada rodada.
"""


class Challenge:
    """Executa o fluxo do RPA Challenge sobre qualquer BrowserDriver."""

    def __init__(self, driver: BrowserDriver, logs: Logs) -> None:
        """
        Args:
            driver: Implementação de BrowserDriver já construída.
            logs: Instância de Logs para registro das operações.
        """
        self.driver = driver
        self.logs = logs

    def iniciar_desafio(self, url: str) -> None:
        """
        Navega para a URL do desafio e clica em 'Start'.

        Deve ser chamado uma única vez antes do preenchimento dos formulários.

        Args:
            url: URL do sistema a ser acessado, proveniente das configurações.
        """
        self.logs.info(f'Navegando para o RPA Challenge com o driver {self.driver.nome}.')
        self.driver.abrir(url)
        self.driver.clicar_iniciar()
        self.logs.info('Desafio iniciado com sucesso.')

    def preencher_formulario(self, item: Item) -> None:
        """
        Preenche todos os campos do formulário e envia.

        Args:
            item: Schema Pydantic com os dados do registro atual,
                  lido da tabela item via get_queued_items_by_run.
        """
        self.logs.info(f'Preenchendo formulário: {item.First_Name} {item.Last_Name}.')

        for rotulo, atributo in CAMPOS_DO_FORMULARIO.items():
            self.driver.preencher_campo(rotulo, getattr(item, atributo))

        self.driver.enviar()

    def capturar_resultado(self) -> str:
        """
        Devolve o texto do resultado final exibido após o último envio.

        A espera pelo elemento é responsabilidade do driver, garantida pelo
        contrato — por isso o retorno é str, e não str | None como antes.

        Returns:
            str: Texto do resultado, ex.: 'Your success rate is 100% ...'.
        """
        resultado = self.driver.ler_resultado()
        self.logs.info(resultado)

        return resultado
