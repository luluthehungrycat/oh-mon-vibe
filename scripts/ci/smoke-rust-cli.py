from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import vibe


def main(omv: Path) -> None:
    package_root = Path(vibe.__file__).parent
    rust_binary = (
        package_root / "_bin" / ("vibe-rs.exe" if os.name == "nt" else "vibe-rs")
    )
    app_server = omv.parent / (
        "omv-app-server.exe" if os.name == "nt" else "omv-app-server"
    )
    if not rust_binary.is_file():
        raise RuntimeError(f"bundled Rust CLI not found: {rust_binary}")
    if not app_server.is_file():
        raise RuntimeError(f"installed OMV app-server not found: {app_server}")

    env = os.environ.copy()
    env["VIBE_CLI"] = "rust"
    direct_version = subprocess.run(
        [str(rust_binary), "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    ).stdout.strip()
    command_version = subprocess.run(
        [str(omv), "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    ).stdout.strip()
    if not direct_version.startswith("omv ") or command_version != direct_version:
        raise RuntimeError(
            f"VIBE_CLI=rust omv did not dispatch to the bundled binary: "
            f"{command_version!r} != {direct_version!r}"
        )
    print("PASS: omv dispatches to the bundled Rust CLI")
    print(f"PASS: bundled Rust CLI sibling app-server exists: {app_server.name}")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    if not arguments:
        raise SystemExit("usage: smoke-rust-cli.py /path/to/omv")
    main(Path(arguments[0]))
