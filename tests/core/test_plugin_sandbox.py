from __future__ import annotations

from pathlib import Path

import pytest

from vibe.core.plugins.sandbox import (
    PLUGIN_STDIO_PROTOCOL,
    PluginCapabilityEvidence,
    PluginSandboxError,
    PluginSandboxPlan,
    require_plugin_isolation,
    select_plugin_sandbox,
)
import vibe.core.safety.sandbox as safety_sandbox
from vibe.core.safety.sandbox import BubblewrapBackend


def test_sandbox_off_does_not_construct_a_backend() -> None:
    assert (
        select_plugin_sandbox(
            "off", "bubblewrap", command="plugin-stdio", cwd=Path(".")
        )
        is None
    )


def test_required_sandbox_refuses_missing_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(safety_sandbox.shutil, "which", lambda _: None)
    with pytest.raises(PluginSandboxError, match="unavailable"):
        select_plugin_sandbox("required", "auto", command="plugin-stdio", cwd=Path("."))


def test_required_isolation_refuses_incomplete_evidence() -> None:
    plan = PluginSandboxPlan(
        BubblewrapBackend("bwrap"),
        ("bwrap",),
        PluginCapabilityEvidence(
            PLUGIN_STDIO_PROTOCOL,
            "bubblewrap",
            network_isolated=True,
            writable_workdir=True,
            timeout_enforced=False,
            cleanup_confirmed=True,
        ),
    )
    with pytest.raises(PluginSandboxError, match="unsandboxed fallback"):
        require_plugin_isolation(
            manifest_expectation="required", policy="required", plan=plan
        )


def test_optional_plugin_can_be_opted_into_host_sandbox() -> None:
    plan = PluginSandboxPlan(
        BubblewrapBackend("bwrap"),
        ("bwrap",),
        PluginCapabilityEvidence(
            PLUGIN_STDIO_PROTOCOL,
            "bubblewrap",
            network_isolated=True,
            writable_workdir=True,
            timeout_enforced=True,
            cleanup_confirmed=True,
        ),
    )
    require_plugin_isolation(
        manifest_expectation="optional", policy="required", plan=plan
    )
