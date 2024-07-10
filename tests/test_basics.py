import subprocess
import os
import pytest

from . import get_file_content

ALL_CREATED_FILES = [
    "requirements-base.in",
    "requirements-base.txt",
    "requirements.in",
    "requirements.txt",
    "requirements-dev.in",
    "requirements-dev.txt",
    "pipt_config.env",
    "pipt_locks.env",
]


def check_created_files(path, check_req_txt_empty: bool = True, uv=True):
    for file_name in ALL_CREATED_FILES:
        assert os.path.isfile(path / file_name)

    req_base_in_content = get_file_content(path / "requirements-base.in")

    assert all(substring in req_base_in_content for substring in ("pip", "wheel"))

    if uv:
        assert "uv" in req_base_in_content
    else:
        assert "pip-tools" in req_base_in_content

    req_base_txt_content = get_file_content(path / "requirements-base.txt")

    assert all(
        substring in req_base_txt_content
        for substring in ("pip==", "wheel==", "--hash=")
    )

    if uv:
        assert "uv==" in req_base_txt_content
    else:
        assert "pip-tools==" in req_base_txt_content

    req_in_content = get_file_content(path / "requirements.in")

    assert (req_in_content.strip()).startswith("-c requirements-base.txt")

    req_txt_content = get_file_content(path / "requirements.txt")
    non_comment_lines = [
        line
        for line in req_txt_content.splitlines()
        if not line.strip().startswith("#")
    ]

    # nothing in requirements.txt
    if check_req_txt_empty:
        assert len(non_comment_lines) == 0

    req_dev_in_content = get_file_content(path / "requirements-dev.in")
    assert "pytest" in req_dev_in_content

    req_dev_txt_content = get_file_content(path / "requirements-dev.txt")
    assert "pytest==" in req_dev_txt_content

    pipt_locks_env_content = get_file_content(path / "pipt_locks.env")

    assert all(
        substring in pipt_locks_env_content
        for substring in (
            "PY_VERSION=",
            "DEPENDENCY_SPECIFICATIONS_ABORT_HASH=",
            "DEPENDENCY_SPECIFICATIONS_FULL_HASH=",
            "PYTHON_ENVIRONMENT_BASE_HASH=",
        )
    )

    pipt_config_env_content = get_file_content(path / "pipt_config.env")

    assert "##### BASIC OPTIONS #####" in pipt_config_env_content


def remove_requests_and_check(
    tmp_path,
    pipt_abs_path,
    env,
):
    # Removing requests
    result = subprocess.run(
        [
            pipt_abs_path,
            "remove",
            "requests",
        ],
        capture_output=True,
        env=env,  # control environment variables
        cwd=tmp_path,
    )

    assert result.returncode == 0
    req_in_content = get_file_content(tmp_path / "requirements.in")

    assert "requests" not in req_in_content

    req_dev_in_content = get_file_content(tmp_path / "requirements-dev.in")

    assert "requests" not in req_dev_in_content

    req_txt_content = get_file_content(tmp_path / "requirements.txt")

    assert "requests==" not in req_txt_content

    req_dev_txt_content = get_file_content(tmp_path / "requirements-dev.txt")

    assert "requests==" not in req_dev_txt_content

    # Check requests not importable any more
    result = subprocess.run(
        [
            pipt_abs_path,
            "run",
            "-s",
            "--",
            "python",
            "-c",
            'import requests; print("Requests version:", requests.__version__)',
        ],
        capture_output=True,
        env=env,  # control environment variables
        cwd=tmp_path,
    )
    assert result.returncode != 0
    result_stdout = result.stdout.decode()
    assert result_stdout == ""
    result_stderr = result.stderr.decode()
    assert "ModuleNotFoundError" in result_stderr


def download_and_check_deps(pipt_abs_path, tmp_path, env, check_requests=True):
    # download deps
    result = subprocess.run(
        [pipt_abs_path, "download", "-s", str(tmp_path / "downloaded")],
        capture_output=True,
        env=env,  # control environment variables
        cwd=tmp_path,
    )

    assert result.returncode == 0
    assert os.path.isdir(tmp_path / "downloaded")
    objects_in_download_dir = os.listdir(tmp_path / "downloaded")
    assert len(objects_in_download_dir) > 0
    assert any("pip-" in file_name for file_name in objects_in_download_dir)
    if check_requests:
        assert any("requests-" in file_name for file_name in objects_in_download_dir)


def check_pipt_shell_and_adding_requests(tmp_path, python_interpreter, use_uv=True):
    pipt_abs_path = os.path.abspath("../pipt")
    new_home = tmp_path / "user_home"
    os.makedirs(new_home)

    env = {
        "HOME": str(new_home),
        "PIPT_PYTHON_INTERPRETER": python_interpreter,
        "PIPT_USE_UV": "true" if use_uv else "false",
    }

    result = subprocess.run(
        [pipt_abs_path, "shell"],
        env=env,  # control environment variables
        cwd=tmp_path,
        input="exit".encode(),  # command to run in the activated shell!
    )

    assert result.returncode == 0

    check_created_files(tmp_path, uv=use_uv)

    # Check: Adding prod dependencies works
    result = subprocess.run(
        [pipt_abs_path, "add", "requests"],
        env=env,  # do not pass environment variables
        cwd=tmp_path,
    )

    assert result.returncode == 0

    check_created_files(tmp_path, check_req_txt_empty=False, uv=use_uv)

    req_in_content = get_file_content(tmp_path / "requirements.in")

    assert "requests" in req_in_content

    req_txt_content = get_file_content(tmp_path / "requirements.txt")

    assert "requests==" in req_txt_content

    # download deps
    download_and_check_deps(pipt_abs_path, tmp_path, env)

    # check requests importable in --prod
    result = subprocess.run(
        [
            pipt_abs_path,
            "run",
            "--prod",
            "-s",
            "--",
            "python",
            "-c",
            'import requests; print("Requests version:", requests.__version__)',
        ],
        capture_output=True,
        env=env,  # control environment variables
        cwd=tmp_path,
        input="exit".encode(),  # command to run in the activated shell!
    )
    assert result.returncode == 0
    result_stdout = result.stdout.decode()
    assert (
        len(result_stdout.splitlines()) == 1
    )  # splitlines strips newline and following empty line
    assert "Requests version: " in result_stdout

    assert (
        len(result_stdout.removeprefix("Requests version: ").split(".")) == 3
    )  # some semantic versioning string

    # check requests importable in dev mode
    result = subprocess.run(
        [
            pipt_abs_path,
            "run",
            "-s",
            "--",
            "python",
            "-c",
            'import requests; print("Requests version:", requests.__version__)',
        ],
        capture_output=True,
        env=env,  # control environment variables
        cwd=tmp_path,
        input="exit".encode(),  # command to run in the activated shell!
    )
    assert result.returncode == 0
    result_stdout = result.stdout.decode()
    assert (
        len(result_stdout.splitlines()) == 1
    )  # splitlines strips newline and following empty line
    assert "Requests version: " in result_stdout

    assert (
        len(result_stdout.removeprefix("Requests version: ").split(".")) == 3
    )  # some semantic versioning string

    # Remove requests
    remove_requests_and_check(
        tmp_path,
        pipt_abs_path,
        env,
    )


@pytest.mark.parametrize("use_uv", [True, False], ids=["using uv", "using pip-tools"])
def test_pipt_shell_creates_everything_and_add_prod_dep(
    tmp_path, use_uv, python_interpreter
):
    check_pipt_shell_and_adding_requests(
        tmp_path, python_interpreter=python_interpreter, use_uv=use_uv
    )


def check_pipt_shell_and_adding_requests_as_dev_dep(
    tmp_path, python_interpreter, use_uv=True
):
    pipt_abs_path = os.path.abspath("../pipt")

    assert len(os.listdir(tmp_path)) == 0

    new_home = tmp_path / "user_home"
    os.makedirs(new_home)

    env = {
        "HOME": str(new_home),
        "PIPT_PYTHON_INTERPRETER": python_interpreter,
        "PIPT_USE_UV": "true" if use_uv else "false",
    }

    result = subprocess.run(
        [pipt_abs_path, "shell"],
        env=env,  # control environment variables
        cwd=tmp_path,
        input="exit".encode(),  # command to run in the activated shell!
    )

    assert result.returncode == 0

    check_created_files(tmp_path, uv=use_uv)

    # Check: Adding prod dependencies works
    result = subprocess.run(
        [pipt_abs_path, "add", "requests", "--dev"],
        env=env,  # do not pass environment variables
        cwd=tmp_path,
    )

    assert result.returncode == 0

    check_created_files(tmp_path, check_req_txt_empty=False, uv=use_uv)

    req_in_content = get_file_content(tmp_path / "requirements.in")

    assert "requests" not in req_in_content

    req_txt_content = get_file_content(tmp_path / "requirements.txt")

    assert "requests==" not in req_txt_content

    req_dev_in_content = get_file_content(tmp_path / "requirements-dev.in")

    assert "requests" in req_dev_in_content

    req_dev_txt_content = get_file_content(tmp_path / "requirements-dev.txt")

    assert "requests==" in req_dev_txt_content

    # download deps
    download_and_check_deps(pipt_abs_path, tmp_path, env)

    # check requests importable in dev
    result = subprocess.run(
        [
            pipt_abs_path,
            "run",
            "-s",
            "--",
            "python",
            "-c",
            'import requests; print("Requests version:", requests.__version__)',
        ],
        capture_output=True,
        env=env,  # control environment variables
        cwd=tmp_path,
        input="exit".encode(),  # command to run in the activated shell!
    )
    assert result.returncode == 0
    result_stdout = result.stdout.decode()
    assert (
        len(result_stdout.splitlines()) == 1
    )  # splitlines strips newline and following empty line
    assert "Requests version: " in result_stdout

    assert (
        len(result_stdout.removeprefix("Requests version: ").split(".")) == 3
    )  # some semantic versioning string

    # Check requests not importable when in prod setup!
    result = subprocess.run(
        [
            pipt_abs_path,
            "run",
            "--prod",
            "-s",
            "--",
            "python",
            "-c",
            'import requests; print("Requests version:", requests.__version__)',
        ],
        capture_output=True,
        env=env,  # control environment variables
        cwd=tmp_path,
    )
    assert result.returncode != 0
    result_stdout = result.stdout.decode()
    result_stderr = result.stderr.decode()
    assert "ModuleNotFoundError" in result_stderr

    # Remove requests
    remove_requests_and_check(
        tmp_path,
        pipt_abs_path,
        env,
    )


@pytest.mark.parametrize("use_uv", [True, False], ids=["using uv", "using pip-tools"])
def test_pipt_shell_creates_everything_and_add_dev_dep(
    tmp_path, use_uv, python_interpreter
):
    check_pipt_shell_and_adding_requests_as_dev_dep(
        tmp_path, python_interpreter=python_interpreter, use_uv=use_uv
    )


@pytest.mark.parametrize("use_uv", [True, False], ids=["using uv", "using pip-tools"])
def test_venv_creation(tmp_path, use_uv, python_interpreter):
    pipt_abs_path = os.path.abspath("../pipt")

    assert len(os.listdir(tmp_path)) == 0

    new_home = tmp_path / "user_home"
    os.makedirs(new_home)

    env = {
        "HOME": str(new_home),
        "PIPT_PYTHON_INTERPRETER": python_interpreter,
        "PIPT_USE_UV": "true" if use_uv else "false",
    }

    result = subprocess.run(
        [pipt_abs_path, "venv"],
        env=env,  # control environment variables
        cwd=tmp_path,
    )

    assert result.returncode == 0

    # Check venv path
    result = subprocess.run(
        [pipt_abs_path, "info", "--venv"],
        env=env,  # control environment variables
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode == 0

    result_stdout = result.stdout.decode()
    path_to_venv = result_stdout.splitlines()[0]

    assert os.path.isdir(path_to_venv)
    objects_in_venv = os.listdir(path_to_venv)
    assert "bin" in objects_in_venv

    # delete it
    result = subprocess.run(
        [pipt_abs_path, "rmvenv"],
        env=env,  # control environment variables
        cwd=tmp_path,
    )
    assert result.returncode == 0

    assert not os.path.exists(path_to_venv)

    # Check venv path
    result = subprocess.run(
        [pipt_abs_path, "info", "--python"],
        env=env,  # control environment variables
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode == 0

    # Check pipt info --python command
    result_stdout = result.stdout.decode()
    python_interpr_from_info = result_stdout.splitlines()[0]
    assert python_interpr_from_info == python_interpreter


@pytest.mark.parametrize("use_uv", [True, False], ids=["using uv", "using pip-tools"])
def test_help_commands(tmp_path, use_uv, python_interpreter):
    pipt_abs_path = os.path.abspath("../pipt")

    assert len(os.listdir(tmp_path)) == 0

    new_home = tmp_path / "user_home"
    os.makedirs(new_home)

    env = {
        "HOME": str(new_home),
        "PIPT_PYTHON_INTERPRETER": python_interpreter,
        "PIPT_USE_UV": "true" if use_uv else "false",
    }

    # usage command
    result = subprocess.run(
        [pipt_abs_path, "usage"],
        env=env,  # control environment variables
        cwd=tmp_path,
        capture_output=True,
    )

    assert result.returncode == 0
    result_stdout = result.stdout.decode()
    assert "pipt shell" in result_stdout
    assert "pipt info" in result_stdout

    # help command
    result = subprocess.run(
        [pipt_abs_path, "help"],
        env=env,  # control environment variables
        cwd=tmp_path,
        capture_output=True,
    )

    assert result.returncode == 0
    result_stdout = result.stdout.decode()
    assert "Details on the available subcommands:" in result_stdout


@pytest.mark.parametrize("use_uv", [True, False], ids=["using uv", "using pip-tools"])
def test_sync_system_and_offline_install(tmp_path, use_uv, python_interpreter):
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

    # Check venv path
    result = subprocess.run(
        [pipt_abs_path, "info", "--venv"],
        env=env,  # control environment variables
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode == 0

    result_stdout = result.stdout.decode()
    path_to_venv = result_stdout.splitlines()[0]

    # remove venv and recreate manually, since we want an empty venv for testing
    # offline sync (pip-sync does not fail if it does not have anything to install)
    result = subprocess.run(
        [pipt_abs_path, "rmvenv"],
        env=env,  # control environment variables
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode == 0

    result = subprocess.run(
        [pipt_abs_path, "venv"],
        env=env,  # control environment variables
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode == 0

    sync_system_env = {
        "HOME": str(new_home),
        "PIPT_PYTHON_INTERPRETER": path_to_venv + "/bin/python",
        "PIPT_USE_UV": "true" if use_uv else "false",
    }
    offline_sync_dir_path = tmp_path / "downloaded"

    sync_system_offline_env = {
        "HOME": str(new_home),
        "PIPT_PYTHON_INTERPRETER": path_to_venv + "/bin/python",
        "PIPT_USE_UV": "true" if use_uv else "false",
        "PIPT_OFFLINE_SYNC_DIR": str(offline_sync_dir_path),
    }

    # sync system from offline before downloading should fail:
    result = subprocess.run(
        [pipt_abs_path, "sync-system"],
        env=sync_system_offline_env,  # control environment variables
        cwd=tmp_path,
    )
    assert result.returncode != 0

    # sync system online should work
    result = subprocess.run(
        [pipt_abs_path, "sync-system"],
        env=sync_system_env,  # control environment variables
        cwd=tmp_path,
    )
    assert result.returncode == 0

    # download dependencies
    download_and_check_deps(pipt_abs_path, tmp_path, env=env, check_requests=False)

    # remove venv and recreate manually, since we want an empty venv for testing
    # offline sync (pip-sync does not fail if it does not have anything to install)
    result = subprocess.run(
        [pipt_abs_path, "rmvenv"],
        env=env,  # control environment variables
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode == 0

    result = subprocess.run(
        [pipt_abs_path, "venv"],
        env=env,  # control environment variables
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode == 0

    # sync system from offline should work now!
    result = subprocess.run(
        [pipt_abs_path, "sync-system"],
        env=sync_system_offline_env,  # control environment variables
        cwd=tmp_path,
    )
    assert result.returncode == 0
