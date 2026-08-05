"""
Ponto de entrada do robô.

    poetry run python bot.py
    poetry run python bot.py --driver selenium
    poetry run python bot.py --help

No topo entram apenas a leitura da linha de comando e a comunicação com o
orquestrador — nenhuma das duas exige configuração. O Alembic e o Execute são
importados dentro do bloco de execução, e isso não é estilo: importar
`resources.execute` abre a cadeia que lê o config.json e monta o engine do
banco. Ali dentro, essa falha acontece **dentro do try** e chega ao painel do
Maestro com a causa real; no topo do arquivo, derrubaria o processo antes de
existir alguém para reportá-la — e faria o `--help` exigir configuração pronta.
"""

from resources.cli import obter_driver_dos_argumentos
from resources.Tools.botcity import conectar, reportar_falha

if __name__ == '__main__':
    driver = obter_driver_dos_argumentos()
    maestro = conectar()

    # Só a partida entra no try. O execute() fica de fora porque já reporta o
    # próprio desfecho: embrulhá-lo aqui faria a mesma falha ser reportada duas
    # vezes, e a segunda chamada poderia estourar mascarando o erro original.
    try:
        from alembic import command
        from alembic.config import Config

        from resources.execute import Execute

        command.upgrade(Config('alembic.ini'), 'head')
        executor = Execute(maestro, driver)
    except Exception as erro:
        reportar_falha(maestro, erro)
        raise

    executor.execute()
