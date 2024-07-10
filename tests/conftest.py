import pytest
import os


@pytest.fixture
def python_interpreter():
    return os.environ.get("FULL_PYTHON_PATH", "/usr/bin/python3.12")
