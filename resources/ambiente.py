"""
Conferência do ambiente antes de o robô começar.

Só a biblioteca padrão entra aqui, e isso é requisito e não estilo: este módulo
precisa ser importável exatamente na máquina em que nada mais está instalado.
"""

import sys

VERSAO_EXIGIDA = (3, 13)


def exigir_python_suportado(versao: tuple[int, ...] = sys.version_info) -> None:
    """
    Encerra com mensagem legível se o interpretador não for o suportado.

    A verificação é de igualdade, e não de mínimo, porque é o que os
    `requirements*.txt` dizem: eles são exportados com o marcador
    ``python_version == "3.13"`` em toda linha. Em qualquer outra versão, o pip
    ignora todas elas, **não instala dependência alguma e ainda assim encerra
    com código 0** — um deploy que confere código de saída vê sucesso. A falha
    só apareceria depois, como um ModuleNotFoundError que não explica a causa.

    Args:
        versao: A versão a conferir. O padrão é a do interpretador em execução;
            o parâmetro existe para o teste conseguir simular outra sem precisar
            de um segundo Python instalado.

    Raises:
        SystemExit: Se a versão em execução não for a exigida.
    """
    if versao[:2] == VERSAO_EXIGIDA:
        return

    exigida = '.'.join(str(parte) for parte in VERSAO_EXIGIDA)
    encontrada = '.'.join(str(parte) for parte in versao[:2])

    raise SystemExit(
        f'Este robô exige Python {exigida}; encontrado {encontrada}.\n'
        f'Os requirements são exportados com o marcador python_version == '
        f'"{exigida}", então em outra versão o pip não instala dependência '
        'alguma e ainda assim reporta sucesso.'
    )
