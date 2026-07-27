import os
import subprocess


def test_detect_manual_pip_install(tmp_path, python_interpreter):
    """Test whether uv detects manual installed packages changes in its venv

    This test requires a uv to be present in the PATH!
    """

    uv_path = os.environ["HOME"] + "/.local/bin/uv"
    project_dir = tmp_path / "myproject"

    uv_env = {}

    # init uv project

    result = subprocess.run(
        [
            uv_path,
            "init",
            "myproject",
        ],
        env=uv_env,  # control environment variables
        cwd=tmp_path,
    )
    assert result.returncode == 0

    # add pip

    result = subprocess.run(
        [
            uv_path,
            "add",
            "pip",
        ],
        env=uv_env,  # control environment variables
        cwd=project_dir,
    )
    assert result.returncode == 0

    # check httpx not in venv

    result = subprocess.run(
        [
            uv_path,
            "run",
            "--",
            "python",
            "-c",
            'import httpx; print("Httpx version:", httpx.__version__)',
        ],
        capture_output=True,
        env=uv_env,  # control environment variables
        cwd=project_dir,
    )
    assert result.returncode != 0
    result_stdout = result.stdout.decode()
    result_stderr = result.stderr.decode()
    assert "ModuleNotFoundError" in result_stderr

    # manually install httpx with uv run -- pip install httpx

    pip_path = project_dir / ".venv" / "bin" / "pip"
    uv_managed_venv_python = project_dir / ".venv" / "bin" / "python"

    print(pip_path)

    result = subprocess.run(
        [uv_path, "run", "--", "pip", "install", "httpx"],
        env=uv_env,  # control environment variables
        cwd=project_dir,
        shell=False,
    )

    assert result.returncode == 0

    # Check httpx present
    result = subprocess.run(
        "source .venv/bin/activate",
        env=uv_env,  # control environment variables
        cwd=project_dir,
        shell=True,
        input='python -c "import httpx" && deactivate'.encode(),  # command to run in the activated shell!
    )

    assert result.returncode == 0

    # check httpx is now present
    print(uv_managed_venv_python)

    result = subprocess.run(
        [
            uv_path,
            "run",
            "--",
            "python",
            "-c",
            "import httpx",
        ],
        capture_output=True,
        # env=uv_env,  # control environment variables
        cwd=project_dir,
    )
    assert result.returncode == 0
    result_stderr = result.stderr.decode()
    assert "ModuleNotFoundError" not in result_stderr

    # Check httpx still present
    result = subprocess.run(
        "source .venv/bin/activate",
        env=uv_env,  # control environment variables
        cwd=project_dir,
        shell=True,
        input='python -c "import httpx" && deactivate'.encode(),  # command to run in the activated shell!
    )

    assert result.returncode == 0
