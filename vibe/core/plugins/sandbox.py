"""Versioned plugin isolation contract backed by host sandbox implementations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from vibe.core.safety.sandbox import BubblewrapBackend, FirejailBackend

PLUGIN_STDIO_PROTOCOL = "omv.plugin.stdio.v1"
PluginSandboxPolicy = Literal["off", "auto", "required"]
PluginSandboxBackend = Literal["auto", "bubblewrap", "firejail"]
PluginSandbox = BubblewrapBackend | FirejailBackend


class PluginSandboxError(RuntimeError):
    pass


class PluginStdioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol: Literal["omv.plugin.stdio.v1"] = PLUGIN_STDIO_PROTOCOL
    request_id: str = Field(min_length=1)
    method: Literal["initialize", "invoke", "shutdown"]
    payload: dict[str, object] = Field(default_factory=dict)


class PluginStdioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol: Literal["omv.plugin.stdio.v1"] = PLUGIN_STDIO_PROTOCOL
    request_id: str = Field(min_length=1)
    ok: bool
    payload: dict[str, object] = Field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class PluginCapabilityEvidence:
    protocol: str
    backend: str
    network_isolated: bool
    writable_workdir: bool
    timeout_enforced: bool
    cleanup_confirmed: bool

    @property
    def complete(self) -> bool:
        return (
            self.protocol == PLUGIN_STDIO_PROTOCOL
            and self.network_isolated
            and self.writable_workdir
            and self.timeout_enforced
            and self.cleanup_confirmed
        )


@dataclass(frozen=True)
class PluginSandboxPlan:
    backend: PluginSandbox
    argv: tuple[str, ...]
    evidence: PluginCapabilityEvidence


def select_plugin_sandbox(
    policy: PluginSandboxPolicy,
    backend: PluginSandboxBackend,
    *,
    command: str,
    cwd: Path,
) -> PluginSandboxPlan | None:
    if policy == "off":
        return None
    selected = _detect_backend(backend)
    if selected is None:
        if policy == "required":
            raise PluginSandboxError("required plugin sandbox backend is unavailable")
        return None
    capabilities = selected.capabilities()
    evidence = PluginCapabilityEvidence(
        protocol=PLUGIN_STDIO_PROTOCOL,
        backend=capabilities.backend,
        network_isolated=capabilities.network_isolation,
        writable_workdir=capabilities.writable_workdir,
        timeout_enforced=False,
        cleanup_confirmed=False,
    )
    if policy == "required" and not evidence.complete:
        raise PluginSandboxError(
            "required plugin sandbox capability evidence is incomplete"
        )
    return PluginSandboxPlan(
        selected, tuple(selected.build_argv(command, cwd)), evidence
    )


def require_plugin_isolation(
    *,
    manifest_expectation: Literal["optional", "required"],
    policy: PluginSandboxPolicy,
    plan: PluginSandboxPlan | None,
) -> None:
    if manifest_expectation != "required" and policy != "required":
        return
    if plan is None or not plan.evidence.complete:
        raise PluginSandboxError(
            "plugin requires complete isolation evidence; unsandboxed fallback is refused"
        )


def _detect_backend(backend: PluginSandboxBackend) -> PluginSandbox | None:
    if backend in {"auto", "bubblewrap"}:
        selected = BubblewrapBackend.detect(network="none")
        if selected is not None:
            return selected
    if backend in {"auto", "firejail"}:
        return FirejailBackend.detect(network="none")
    return None


__all__ = [
    "PLUGIN_STDIO_PROTOCOL",
    "PluginCapabilityEvidence",
    "PluginSandboxError",
    "PluginSandboxPlan",
    "PluginStdioRequest",
    "PluginStdioResponse",
    "require_plugin_isolation",
    "select_plugin_sandbox",
]
