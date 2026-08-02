"""
Dublê de navegador para os testes do fluxo de negócio.

Não herda de BrowserDriver e não importa nada de resources: a conformidade com
o Protocol é estrutural, e é justamente isso que permite o teste viver fora da
hierarquia do código de produção.

Em vez de dirigir uma tela, registra as chamadas recebidas — o que transforma
"o robô preencheu os sete campos com os valores certos" numa asserção de
dicionário, sem navegador, em milissegundos.
"""

RESULTADO_PADRAO = 'Your success rate is 100% ( 70 out of 70 fields) in 678 milliseconds'


class FakeDriver:
    """Implementação de BrowserDriver que grava o que foi pedido."""

    nome = 'fake'

    def __init__(self, resultado: str = RESULTADO_PADRAO):
        """
        Args:
            resultado: Texto que ler_resultado() devolverá.
        """
        self.chamadas: list[tuple] = []
        self.campos_preenchidos: dict[str, str] = {}
        self._resultado = resultado

    @property
    def operacoes(self) -> list[str]:
        """Só os nomes das operações, na ordem — para asserções de sequência."""
        return [chamada[0] for chamada in self.chamadas]

    def abrir(self, url: str) -> None:
        self.chamadas.append(('abrir', url))

    def clicar_iniciar(self) -> None:
        self.chamadas.append(('clicar_iniciar',))

    def preencher_campo(self, rotulo: str, valor: str) -> None:
        self.chamadas.append(('preencher_campo', rotulo, valor))
        self.campos_preenchidos[rotulo] = valor

    def enviar(self) -> None:
        self.chamadas.append(('enviar',))

    def ler_resultado(self) -> str:
        self.chamadas.append(('ler_resultado',))
        return self._resultado

    def fechar(self) -> None:
        self.chamadas.append(('fechar',))
