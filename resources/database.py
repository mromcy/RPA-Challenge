"""
SQLAlchemy engine and session management.
"""

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from resources.settings import get_settings

# Engine shared by the whole project.
# pool_pre_ping=True avoids silent errors from stale connections after a long
# idle period.
engine = create_engine(
    get_settings().DATABASE_URL,
    connect_args={
        'connect_timeout': 10,
        # Forces the server timezone to America/Fortaleza on every session
        'options': '-c timezone=America/Fortaleza',
    },
    # Maximum time to obtain a connection from the pool (seconds)
    pool_timeout=30,
    # Recycle connections after 30 min to avoid dead ones
    pool_recycle=1800,
    # Connections kept open simultaneously in the pool
    pool_size=10,
    # Extra connections allowed beyond pool_size at peak load
    max_overflow=20,
    pool_pre_ping=True,
)


@contextmanager
def get_session():
    """
    A session that commits on the way out and rolls back on an exception::

        with get_session() as session:
            session.add(obj)
            session.flush()
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
