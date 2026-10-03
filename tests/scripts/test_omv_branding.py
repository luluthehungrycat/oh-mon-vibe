from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[2]
CHECKER = ROOT / "scripts" / "check_omv_branding.py"


def run_checker(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_repository_passes_branding_invariants() -> None:
    result = run_checker(ROOT)
    assert result.returncode == 0, result.stderr


def test_checker_rejects_upstream_package_name(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "mistral-vibe"\n'
        'urls = { Repository = "https://github.com/luluthehungrycat/oh-my-vibe" }\n'
        "[project.scripts]\n"
        'omv = "vibe.cli.launcher:main"\n'
        'omv-acp = "vibe.acp.entrypoint:main"\n'
        'omv-app-server = "vibe.app_server.stdio:main"\n',
        encoding="utf-8",
    )
    (tmp_path / "vibe" / "utils").mkdir(parents=True)
    (tmp_path / "vibe" / "utils" / "paths.py").write_text(
        'Path.home() / ".omv"\nos.getenv("OMV_HOME")\n', encoding="utf-8"
    )
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert "project.name must be oh-my-vibe" in result.stderr


def test_checker_rejects_vibe_home_override(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "oh-my-vibe"\n'
        'urls = { Repository = "https://github.com/luluthehungrycat/oh-my-vibe" }\n'
        "[project.scripts]\n"
        'omv = "vibe.cli.launcher:main"\n'
        'omv-acp = "vibe.acp.entrypoint:main"\n'
        'omv-app-server = "vibe.app_server.stdio:main"\n',
        encoding="utf-8",
    )
    (tmp_path / "vibe" / "utils").mkdir(parents=True)
    (tmp_path / "vibe" / "utils" / "paths.py").write_text(
        'Path.home() / ".omv"\nos.getenv("OMV_HOME")\nos.getenv("VIBE_HOME")\n',
        encoding="utf-8",
    )
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert "VIBE_HOME" in result.stderr
