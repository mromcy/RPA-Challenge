"""
Contrato que o fluxo de negócio usa para falar com o navegador.

Este módulo não importa Playwright nem Selenium, e não deve importar. Ele é o
único ponto que tanto o fluxo (Modules/challenge.py) quanto as implementações
(Drivers/playwright_driver.py, Drivers/selenium_driver.py) podem conhecer sem
arrastar uma biblioteca de navegador junto — é isso que permite testar o fluxo
sem browser algum.

As operações falam a língua do desafio ("preencher o campo com este rótulo"),
não a da biblioteca ("page.locator(...).fill(...)").
"""

from typing import Protocol

TIMEOUT_PADRAO_MS = 30_000
"""
Tempo-limite de toda espera, em milissegundos, compartilhado pelos dois drivers.

Mora aqui, e não dentro de cada implementação, porque a comparação do benchmark
só vale se os dois tiverem a mesma paciência. Números diferentes fariam um
desistir antes do outro em caso de lentidão, e a diferença apareceria na tabela
como se fosse mérito da biblioteca.
"""


class BrowserDriver(Protocol):
    """
    Operações que o desafio precisa de um navegador.

    Protocol e não classe base abstrata: a conformidade é estrutural, ou seja,
    basta a classe ter os métodos com as assinaturas certas. Nenhuma
    implementação precisa herdar deste contrato nem importá-lo — inclusive o
    FakeDriver dos testes, que vive em tests/ e não conhece resources/.

    A verificação é estática: quem cobra um método faltando é o type checker,
    não o interpretador.
    """

    nome: str
    """Identifica o driver nos logs e na tabela do benchmark."""

    def abrir(self, url: str) -> None:
        """Sobe o navegador, se ainda não estiver de pé, e navega até a URL."""
        ...

    def clicar_iniciar(self) -> None:
        """Clica no botão 'Start'. Fronteira entre partida e preenchimento."""
        ...

    def preencher_campo(self, rotulo: str, valor: str) -> None:
        """
        Preenche o campo identificado pelo rótulo visível na tela.

        Um método para todos os campos, endereçados por rótulo, para que a
        interface não cresça a cada campo novo no formulário.
        """
        ...

    def enviar(self) -> None:
        """Clica em 'Submit', enviando o formulário atual."""
        ...

    def ler_resultado(self) -> str:
        """
        Espera o resultado final aparecer e devolve o texto.

        O retorno é str e não str | None de propósito: a espera é obrigação da
        implementação, não sorte de quem chama.
        """
        ...

    def fechar(self) -> None:
        """Encerra o navegador e libera os recursos."""
        ...
