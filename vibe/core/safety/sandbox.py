"""Sandbox backend contracts and Linux Bubblewrap/Firejail implementations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Literal

from vibe.core.utils.shell import shell_executable


class SandboxError(RuntimeError):
    """The sandbox could not be started before the command ran."""


@dataclass(frozen=True)
class SandboxCapabilities:
    backend: str
    available: bool
    network_isolation: bool
    writable_workdir: bool
    reason: str = ""


def _shell_argv(command: str) -> list[str]:
    shell = shell_executable()
    shell_name = Path(shell).name
    shell_flags = ["--noprofile", "--norc", "-lc"] if shell_name == "bash" else ["-lc"]
    return [shell, *shell_flags, command]


@dataclass(frozen=True)
class BubblewrapBackend:
    executable: str
    network: Literal["none", "host"] = "none"

    @classmethod
    def detect(
        cls, network: Literal["none", "host"] = "none"
    ) -> BubblewrapBackend | None:
        executable = shutil.which("bwrap")
        return cls(executable, network) if executable else None

    def capabilities(self) -> SandboxCapabilities:
        return SandboxCapabilities(
            backend="bubblewrap",
            available=True,
            network_isolation=self.network == "none",
            writable_workdir=True,
        )

    def argv(
        self, command: str, cwd: Path, *, private_home: Path | None = None
    ) -> list[str]:
        """Build a namespace with read-only host files and writable project cwd."""
        del private_home
        args = [
            self.executable,
            "--die-with-parent",
            "--new-session",
            "--ro-bind",
            "/",
            "/",
            "--bind",
            str(cwd),
            str(cwd),
            "--tmpfs",
            "/tmp",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--chdir",
            str(cwd),
            "--setenv",
            "HOME",
            "/tmp",
        ]
        if self.network == "none":
            args.append("--unshare-net")
        args.extend(["--", *_shell_argv(command)])
        return args

    def build_argv(
        self, command: str, cwd: Path, *, private_home: Path | None = None
    ) -> list[str]:
        return self.argv(command, cwd, private_home=private_home)


@dataclass(frozen=True)
class FirejailBackend:
    executable: str
    network: Literal["none", "host"] = "none"

    @classmethod
    def detect(
        cls, network: Literal["none", "host"] = "none"
    ) -> FirejailBackend | None:
        executable = shutil.which("firejail")
        return cls(executable, network) if executable else None

    def capabilities(self) -> SandboxCapabilities:
        return SandboxCapabilities(
            backend="firejail",
            available=True,
            network_isolation=self.network == "none",
            writable_workdir=True,
        )

    def argv(
        self, command: str, cwd: Path, *, private_home: Path | None = None
    ) -> list[str]:
        """Build Firejail argv; the worktree is mapped as the sandbox home."""
        private_option = f"--private={private_home or cwd}"
        args = [self.executable, "--quiet", private_option, "--env=HOME=/tmp"]
        if self.network == "none":
            args.append("--net=none")
        args.extend(["--", *_shell_argv(command)])
        return args

    def build_argv(
        self, command: str, cwd: Path, *, private_home: Path | None = None
    ) -> list[str]:
        return self.argv(command, cwd, private_home=private_home)


__all__ = [
    "BubblewrapBackend",
    "FirejailBackend",
    "SandboxCapabilities",
    "SandboxError",
]
