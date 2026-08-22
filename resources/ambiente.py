"""
Conferência do ambiente antes de o robô começar.

Só a biblioteca padrão entra aqui, e isso é requisito e não estilo: este módulo
precisa ser importável exatamente na máquina em que nada mais está instalado.
"""

import sys

VERSAO_MINIMA = (3, 11)
"""
Menor Python aceito, inclusivo.

Não é escolha de gosto: é o piso que as dependências declaram. Dos 60 pacotes
instalados, numpy e pandas são os mais exigentes, e ambos pedem `>=3.11`.
"""

VERSAO_ACIMA_DA_MAXIMA = (3, 14)
"""
Primeira versão **não** aceita, exclusivo.

O teto tem dono: o `psycopg-binary` publica wheel por versão de interpretador, e
a 3.2.9 — fixada com `==` no pyproject.toml — vai até cp313. Em 3.14 o pip não
encontra binário, tenta compilar da fonte e precisa de libpq e compilador C, o
que não existe numa estação Windows comum. Quando o psycopg subir para uma
versão com wheel cp314, este teto pode subir junto.
"""

VERSAO_EM_USO = (sys.version_info.major, sys.version_info.minor)
"""
Versão do interpretador que está rodando, como par de inteiros.

Extraída campo a campo, e não de `sys.version_info` inteiro, porque aquele
objeto tem cinco posições e a quarta é texto (`'final'`, `'beta'`) — não é uma
tupla de inteiros, por mais que as duas primeiras posições pareçam.
"""


def exigir_python_suportado(versao: tuple[int, ...] = VERSAO_EM_USO) -> None:
    """
    Encerra com mensagem legível se o interpretador estiver fora da faixa.

    Fora dela o problema não se anuncia sozinho: os `requirements*.txt` são
    exportados com marcadores dessa mesma faixa, e o pip **ignora toda linha que
    não casa, não instala nada e ainda assim encerra com código 0** — um deploy
    que confere código de saída vê sucesso. A falha só apareceria depois, como
    um ModuleNotFoundError que nomeia um pacote em vez da causa.

    Args:
        versao: A versão a conferir. O padrão é a do interpretador em execução;
            o parâmetro existe para o teste conseguir simular outra sem precisar
            de um segundo Python instalado.

    Raises:
        SystemExit: Se a versão em execução estiver fora da faixa suportada.
    """
    if VERSAO_MINIMA <= versao[:2] < VERSAO_ACIMA_DA_MAXIMA:
        return

    def formatar(partes: tuple[int, ...]) -> str:
        return '.'.join(str(parte) for parte in partes)

    raise SystemExit(
        f'Este robô exige Python >= {formatar(VERSAO_MINIMA)} e '
        f'< {formatar(VERSAO_ACIMA_DA_MAXIMA)}; encontrado '
        f'{formatar(versao[:2])}.\n'
        'Os requirements são exportados com marcadores dessa faixa, então fora '
        'dela o pip não instala dependência alguma e ainda assim reporta '
        'sucesso.'
    )
