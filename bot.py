"""
Ponto de entrada do robô.

    poetry run python bot.py
    poetry run python bot.py --driver selenium
    poetry run python bot.py --help

Só o módulo de linha de comando é importado no topo. O orquestrador e o Alembic
entram dentro do bloco de execução porque importá-los tem custo real: o
resources.execute abre a cadeia que cria o engine do banco em tempo de import e
exige config.json com credenciais válidas. Mantê-los aqui embaixo faz o --help
funcionar num clone recém-feito, antes de a configuração existir.
"""

from resources.cli import obter_driver_dos_argumentos

if __name__ == '__main__':
    driver = obter_driver_dos_argumentos()

    from alembic import command
    from alembic.config import Config

    from resources.execute import Execute

    alembic_cfg = Config('alembic.ini')
    command.upgrade(alembic_cfg, 'head')

    Execute(driver).execute()
