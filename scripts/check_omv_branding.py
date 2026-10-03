from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tomllib

REQUIRED_SCRIPTS = {
    "omv": "vibe.cli.launcher:main",
    "omv-acp": "vibe.acp.entrypoint:main",
    "omv-app-server": "vibe.app_server.stdio:main",
}
FORBIDDEN_SCRIPTS = {"vibe", "vibe-acp", "vibe-app-server"}


def check_repository(root: Path) -> list[str]:
    errors: list[str] = []
    pyproject_path = root / "pyproject.toml"
    try:
        project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["project"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        return [f"cannot read project metadata: {exc}"]

    if project.get("name") != "oh-my-vibe":
        errors.append("project.name must be oh-my-vibe")

    scripts = project.get("scripts", {})
    if scripts != REQUIRED_SCRIPTS:
        errors.append(f"project.scripts must equal {REQUIRED_SCRIPTS!r}")
    forbidden = FORBIDDEN_SCRIPTS & scripts.keys()
    if forbidden:
        errors.append(
            f"upstream executable names must not be packaged: {sorted(forbidden)!r}"
        )

    urls = project.get("urls", {})
    repository_url = "https://github.com/luluthehungrycat/oh-my-vibe"
    if urls.get("Repository") != repository_url:
        errors.append("project.urls.Repository must point to the Oh My Vibe repository")

    paths = root / "vibe" / "utils" / "paths.py"
    try:
        path_source = paths.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read path implementation: {exc}")
    else:
        if 'Path.home() / ".omv"' not in path_source:
            errors.append("default global state directory must be ~/.omv")
        if 'os.getenv("OMV_HOME")' not in path_source:
            errors.append("global state override must be OMV_HOME")
        if 'os.getenv("VIBE_HOME")' in path_source:
            errors.append("VIBE_HOME must not be consulted as an end-user override")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Oh My Vibe branding invariants")
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = check_repository(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Oh My Vibe branding invariants passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
