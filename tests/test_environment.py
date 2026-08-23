"""
Tests for resources/environment.py — the check made before anything else.

The `version` parameter exists for these tests: without it, verifying the
refusal would take a second interpreter installed on the machine running the
suite.
"""

import ast
import sys
from pathlib import Path

import pytest

from resources.environment import require_supported_python

MODULE = Path(__file__).resolve().parents[1] / 'resources' / 'environment.py'


@pytest.mark.parametrize('minor', [11, 12, 13])
def test_every_version_in_the_range_passes_without_complaint(minor):
    require_supported_python((3, minor, 4))


def test_a_version_below_the_floor_is_refused_naming_what_was_found():
    with pytest.raises(SystemExit) as error:
        require_supported_python((3, 10, 14))

    assert '3.11' in str(error.value)
    assert '3.10' in str(error.value)


def test_a_version_above_the_ceiling_is_refused_too():
    """
    The easiest case to get wrong, because "newer" sounds like "compatible": on
    3.14 the pinned `psycopg-binary` has no wheel, and before that pip already
    ignores every line of the requirements, installs nothing and exits
    successfully.
    """
    with pytest.raises(SystemExit):
        require_supported_python((3, 14, 0))


def test_the_module_imports_nothing_outside_the_standard_library():
    """
    The property that gives the guard its meaning: it has to run on exactly the
    machine where no dependency was installed. A third-party import here would
    make the module blow up before it could explain what happened — and
    ModuleNotFoundError would once again be the only message available.
    """
    tree = ast.parse(MODULE.read_text(encoding='utf-8'))

    imported = {
        (node.module or '').split('.')[0]
        if isinstance(node, ast.ImportFrom)
        else alias.name.split('.')[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert imported <= set(sys.stdlib_module_names), imported
