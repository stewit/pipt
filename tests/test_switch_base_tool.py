import os
import subprocess
import pytest

from . import get_file_content


@pytest.mark.parametrize("use_uv", [True, False], ids=["using uv", "using pip-tools"])
def test_switch_base_tool(tmp_path, use_uv):
    python_interpreter = "/usr/bin/python3.12"

    pipt_abs_path = os.path.abspath("../pipt")

    assert len(os.listdir(tmp_path)) == 0

    new_home = tmp_path / "user_home"
    os.makedirs(new_home)

    env = {
        "HOME": str(new_home),
        "PIPT_PYTHON_INTERPRETER": python_interpreter,
        "PIPT_USE_UV": "true" if use_uv else "false",
    }

    # create a venv, we will use as target for sync system
    result = subprocess.run(
        [pipt_abs_path, "shell"],
        env=env,  # control environment variables
        cwd=tmp_path,
        input="exit".encode(),  # command to run in the activated shell!
    )

    assert result.returncode == 0

    req_base_in_content = get_file_content(tmp_path / "requirements-base.in")

    if use_uv:
        assert "uv" in req_base_in_content
    else:
        assert "pip-tools" in req_base_in_content

    req_base_txt_content = get_file_content(tmp_path / "requirements-base.txt")

    if use_uv:
        assert "uv==" in req_base_txt_content
    else:
        assert "pip-tools==" in req_base_txt_content

    pipt_lock_content = get_file_content(tmp_path / "pipt_locks.env")

    if use_uv:
        assert "USE_UV=true" in pipt_lock_content
        new_pipt_lock_content = pipt_lock_content.replace("USE_UV=true", "USE_UV=false")
    else:
        assert "USE_UV=false" in pipt_lock_content
        new_pipt_lock_content = pipt_lock_content.replace("USE_UV=false", "USE_UV=true")

    # switch base tool by changing lock file
    with open(tmp_path / "pipt_locks.env", "w") as f:
        f.write(new_pipt_lock_content)

    pipt_lock_content = get_file_content(tmp_path / "pipt_locks.env")

    if use_uv:
        assert "USE_UV=false" in pipt_lock_content
    else:
        assert "USE_UV=true" in pipt_lock_content

    env = {
        "HOME": str(new_home),
        "PIPT_PYTHON_INTERPRETER": python_interpreter,
    }

    result = subprocess.run(
        [pipt_abs_path, "shell"],
        env=env,  # control environment variables
        cwd=tmp_path,
        input="exit".encode(),  # command to run in the activated shell!
    )
    assert result.returncode == 0

    req_base_in_content = get_file_content(tmp_path / "requirements-base.in")

    if use_uv:
        assert "pip-tools" in req_base_in_content
    else:
        assert "uv" in req_base_in_content

    req_base_txt_content = get_file_content(tmp_path / "requirements-base.txt")

    if use_uv:
        assert "pip-tools==" in req_base_txt_content
    else:
        assert "uv==" in req_base_txt_content
