"""
Leitura dos argumentos de linha de comando do robô.

Mora fora do bot.py para que o ponto de entrada continue sendo só ponto de
entrada, e para que esta lógica seja testável: importar o bot.py arrasta o
orquestrador e, com ele, a conexão com o banco.

A separação segue o padrão do resto do projeto — separar_driver é função pura e
concentra a regra; obter_driver_dos_argumentos é a casca fina que lê e reescreve
o estado global.
"""

import argparse
import sys

from resources.Drivers.factory import DRIVERS_DISPONIVEIS


def separar_driver(argv: list[str]) -> tuple[str | None, list[str]]:
    """
    Extrai --driver da linha de comando e devolve o que sobrou.

    Usa parse_known_args() e não parse_args() porque o robô também é disparado
    pelo BotCity Maestro, que acrescenta argumentos próprios. O parse_args
    encerraria o programa ao ver o primeiro argumento desconhecido — ou seja,
    o robô morreria na largada sempre que o orquestrador o chamasse.

    Args:
        argv: Linha de comando completa, incluindo o nome do script na posição 0.

    Returns:
        tuple[str | None, list[str]]: O driver pedido (None se ausente) e a
            linha de comando sem os argumentos consumidos, com o nome do script
            preservado na posição 0.

    Raises:
        SystemExit: Se --driver receber um valor fora de DRIVERS_DISPONIVEIS, ou
            se --help for pedido. Comportamento padrão do argparse.
    """
    parser = argparse.ArgumentParser(
        prog='bot.py',
        description='Executa o RPA Challenge.',
    )
    parser.add_argument(
        '--driver',
        choices=DRIVERS_DISPONIVEIS,
        help='Biblioteca que dirige o navegador. Padrão: DRIVER do config.json.',
    )

    argumentos, restante = parser.parse_known_args(argv[1:])

    return argumentos.driver, [argv[0], *restante]


def obter_driver_dos_argumentos() -> str | None:
    """
    Lê --driver de sys.argv e o remove de lá.

    A remoção não é cosmética. O BotMaestroSDK.from_sys_args() lê a linha de
    comando **por posição**, desempacotando sys.argv[1:] como
    (server, task_id, token, organization). Um argumento extra antes deles
    desloca tudo: o robô tentaria se conectar a um servidor chamado '--driver'.
    Retirar o que já foi consumido devolve ao SDK exatamente a linha que ele
    espera, independentemente de onde o --driver tenha sido escrito.

    Returns:
        str | None: Nome do driver, ou None se não foi informado.
    """
    driver, restante = separar_driver(sys.argv)
    sys.argv = restante

    return driver
