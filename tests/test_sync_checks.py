import os
import subprocess
import pytest


@pytest.mark.parametrize("use_uv", [True, False], ids=["using uv", "using pip-tools"])
def test_sync_freeze_check(tmp_path, use_uv, python_interpreter):
    pipt_abs_path = os.path.abspath("../pipt")

    assert len(os.listdir(tmp_path)) == 0

    new_home = tmp_path / "user_home"
    os.makedirs(new_home)

    env = {
        "HOME": str(new_home),
        "PIPT_PYTHON_INTERPRETER": python_interpreter,
        "PIPT_USE_UV": "true" if use_uv else "false",
    }

    # create a synced venv
    result = subprocess.run(
        [pipt_abs_path, "shell"],
        env=env,
        cwd=tmp_path,
        input="exit".encode(),
    )

    assert result.returncode == 0

    # Check venv path
    result = subprocess.run(
        [pipt_abs_path, "info", "--venv"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode == 0

    result_stdout = result.stdout.decode()
    path_to_venv = result_stdout.splitlines()[0]

    assert os.path.isfile(os.path.join(path_to_venv, "frozen_hash.txt"))

    # Second run should not sync again
    result = subprocess.run(
        [pipt_abs_path, "shell"],
        env=env,
        cwd=tmp_path,
        input="exit".encode(),
        capture_output=True,
    )

    assert result.returncode == 0
    result_stdout = result.stdout.decode()
    assert (
        "Existing virtual environment is still in sync. Not syncing again"
        in result_stdout
    )

    # Now we pip install something manual into the venv!

    result = subprocess.run(
        [pipt_abs_path, "run", "--", "pip", "install", "requests"],
        env=env,
        cwd=tmp_path,
    )

    assert result.returncode == 0

    # Now syncing should actually happen, since venv is not in sync!
    result = subprocess.run(
        [pipt_abs_path, "shell"],
        env=env,
        cwd=tmp_path,
        input="exit".encode(),
        capture_output=True,
    )

    assert result.returncode == 0
    result_stdout = result.stdout.decode()
    assert "Syncing virtual environment with" in result_stdout

    # Another run: Syncing should not happen!
    result = subprocess.run(
        [pipt_abs_path, "shell"],
        env=env,
        cwd=tmp_path,
        input="exit".encode(),
        capture_output=True,
    )

    assert result.returncode == 0
    result_stdout = result.stdout.decode()
    assert (
        "Existing virtual environment is still in sync. Not syncing again"
        in result_stdout
    )
