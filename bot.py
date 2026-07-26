from alembic import command
from alembic.config import Config

from resources.execute import Execute

if __name__ == '__main__':
    alembic_cfg = Config('alembic.ini')
    command.upgrade(alembic_cfg, 'head')

    Execute().execute()
