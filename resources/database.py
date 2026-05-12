"""
Configuração do engine SQLAlchemy e gerenciamento de sessões.

Este módulo expõe:
- engine: instância global do SQLAlchemy Engine conectada ao PostgreSQL.
- get_session(): context manager que abre, commita e fecha sessões de forma segura.
"""

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from resources.settings import Settings

# Engine compartilhado por todo o projeto.
# pool_pre_ping=True evita erros silenciosos com conexões stale após idle longo.
engine = create_engine(
    Settings().DATABASE_URL,  # type: ignore[call-arg]
    connect_args={
        'connect_timeout': 10,
        # Força o timezone do servidor para America/Fortaleza em todas as sessões
        'options': '-c timezone=America/Fortaleza',
    },
    # Tempo máximo para obter uma conexão do pool (segundos)
    pool_timeout=30,
    # Recicla conexões após 30 min para evitar conexões mortas
    pool_recycle=1800,
    # Conexões mantidas abertas simultaneamente no pool
    pool_size=10,
    # Conexões extras permitidas além do pool_size em pico de carga
    max_overflow=20,
    pool_pre_ping=True,
)


@contextmanager
def get_session():
    """
    Context manager para sessões de banco de dados.

    Commita automaticamente ao sair do bloco com sucesso.
    Faz rollback e re-lança a exceção em caso de erro.

    Exemplo de uso::

        with get_session() as session:
            session.add(obj)
            session.flush()
            id_ = obj.id

    Yields:
        Session: Sessão SQLAlchemy pronta para uso.
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
