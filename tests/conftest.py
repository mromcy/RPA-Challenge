"""
Fixtures compartilhadas por toda a suíte.

O pytest carrega este arquivo automaticamente — nenhum teste precisa importá-lo.
"""

import pytest

from resources.settings import get_settings


@pytest.fixture(autouse=True)
def _config_limpa():
    """
    Zera o cache de configuração antes e depois de cada teste.

    get_settings() é memoizado com @lru_cache, ou seja, estado global mutável.
    Sem esta limpeza, um teste que leia o config.json real deixa a configuração
    da máquina disponível para os testes seguintes, e o resultado da suíte passa
    a depender da ordem de execução — a categoria de falha mais difícil de
    diagnosticar. Nenhum teste herda a máquina de quem rodou antes dele.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
