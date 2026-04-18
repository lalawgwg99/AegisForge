from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def _venv_python(venv_dir: Path) -> Path:
    scripts = "Scripts" if os.name == "nt" else "bin"
    return venv_dir / scripts / "python"


def _venv_executable(venv_dir: Path, name: str) -> Path:
    scripts = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return venv_dir / scripts / f"{name}{suffix}"


@pytest.mark.integration
def test_hermes_install_and_smoke(tmp_path: Path):
    if os.environ.get("AEGISFORGE_RUN_INTEGRATION") != "1":
        pytest.skip("Set AEGISFORGE_RUN_INTEGRATION=1 to run integration tests.")

    repo_root = Path(__file__).resolve().parents[1]
    venv_dir = tmp_path / ".venv-hermes-smoke"
    root_dir = tmp_path / ".aegisforge-hermes"

    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    python_exe = _venv_python(venv_dir)
    aegisforge_exe = _venv_executable(venv_dir, "aegisforge")

    subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(python_exe), "-m", "pip", "install", "-e", ".[all,dev]"], cwd=repo_root, check=True)

    subprocess.run(
        [
            str(aegisforge_exe),
            "--root",
            str(root_dir),
            "capture",
            "--source",
            "hermes",
            "--type",
            "timeout",
            "--message",
            "request timeout 30s",
        ],
        check=True,
    )
    subprocess.run([str(aegisforge_exe), "--root", str(root_dir), "distill", "--max", "1"], check=True)
    subprocess.run([str(aegisforge_exe), "--root", str(root_dir), "health"], check=True)

    subprocess.run(
        [str(python_exe), "-m", "aegisforge.mcp_server", "--help"],
        env={**os.environ, "AEGISFORGE_ROOT": str(root_dir)},
        check=True,
    )
