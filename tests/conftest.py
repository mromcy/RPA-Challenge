"""
Fixtures shared by the whole suite.

pytest loads this file automatically — no test needs to import it.
"""

import pytest

from resources.settings import get_settings


@pytest.fixture(autouse=True)
def _clean_config():
    """
    Clears the settings cache before and after every test.

    get_settings() is memoised with @lru_cache, which is to say it is mutable
    global state. Without this cleanup, a test that reads the real config.json
    leaves the machine's configuration available to the tests that follow, and
    the suite's result starts depending on execution order — the hardest class
    of failure to diagnose. No test inherits the machine from whoever ran
    before it.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
