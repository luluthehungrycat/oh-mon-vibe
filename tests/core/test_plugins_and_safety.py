from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import time
from typing import Any, Literal

import pytest

from vibe.core.plugins import (
    PLUGIN_CAPABILITIES,
    PluginManifest,
    PluginRegistry,
    discover_plugins,
)
import vibe.core.plugins.registry as plugin_registry
from vibe.core.safety.llm import LLMAnalyzer
from vibe.core.safety.policy import (
    CommandDecision,
    Decision,
    combine_advisory_decisions,
    compose_policy_decision,
    evaluate_advisory_analyzers,
)
from vibe.core.safety.sandbox import BubblewrapBackend, FirejailBackend
from vibe.core.tools.base import BaseToolState, ToolPermission
from vibe.core.tools.builtins.bash import Bash, BashArgs, BashToolConfig


def test_plugin_manifest_requires_supported_contract() -> None:
    manifest = PluginManifest("demo", "1.0", "1", "analyzer")
    manifest.validate()
    with pytest.raises(ValueError, match="unsupported plugin API"):
        replace(manifest, api_version="999").validate()
    with pytest.raises(ValueError, match="unsupported plugin capabilities"):
        replace(manifest, capabilities=frozenset({"network"})).validate()
    with pytest.raises(ValueError, match="not valid for plugin kind"):
        replace(manifest, capabilities=frozenset({"sandbox_backend"})).validate()
    with pytest.raises(ValueError, match="process-isolated plugins are unsupported"):
        replace(manifest, trust="process_isolated").validate()
    assert PLUGIN_CAPABILITIES == frozenset({"analyzer", "sandbox_backend"})


def test_registry_rejects_duplicate_plugins() -> None:
    registry = PluginRegistry()

    class Plugin:
        manifest = PluginManifest("demo", "1.0", "1", "analyzer")

        def register(self, registry: PluginRegistry) -> None:
            pass

    registry.register_plugin(Plugin())
    with pytest.raises(ValueError, match="duplicate plugin"):
        registry.register_plugin(Plugin())


def test_plugin_discovery_records_registration_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenEntryPoint:
        name = "broken"

        def load(self) -> object:
            raise RuntimeError("boom")

    monkeypatch.setattr(
        plugin_registry, "entry_points", lambda **kwargs: [BrokenEntryPoint()]
    )

    registry = discover_plugins({"broken"})

    assert registry.manifests == {}
    assert len(registry.diagnostics) == 1
    diagnostic = registry.diagnostics[0]
    assert diagnostic.plugin == "broken"
    assert diagnostic.event == "registration_failed"
    assert diagnostic.reason == "boom"
    assert diagnostic.trust == "trusted_in_process"
    assert diagnostic.isolation == "in_process"


def test_plugin_discovery_records_manifest_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InvalidPlugin:
        manifest = PluginManifest(
            "invalid", "1.0", "1", "analyzer", frozenset({"sandbox_backend"})
        )

        def register(self, registry: PluginRegistry) -> None:
            raise AssertionError("invalid plugin must not register")

    class InvalidEntryPoint:
        name = "invalid"

        def load(self) -> object:
            return InvalidPlugin()

    monkeypatch.setattr(
        plugin_registry, "entry_points", lambda **kwargs: [InvalidEntryPoint()]
    )

    registry = discover_plugins({"invalid"})

    assert registry.manifests == {}
    assert len(registry.diagnostics) == 1
    diagnostic = registry.diagnostics[0]
    assert diagnostic.plugin == "invalid"
    assert diagnostic.event == "manifest_rejected"
    assert "not valid for plugin kind" in diagnostic.reason


def test_advisory_analyzer_cannot_override_core_deny() -> None:
    core = CommandDecision(Decision.DENY, "denylist", "core")
    advisory = [CommandDecision(Decision.ALLOW, "looks safe", "llm")]
    assert combine_advisory_decisions(core, advisory) == core


def test_ambiguous_advisory_result_requests_human() -> None:
    core = CommandDecision(Decision.SANDBOX, "sandboxable", "core")
    advisory = [CommandDecision(Decision.ASK, "uncertain", "llm")]
    assert combine_advisory_decisions(core, advisory).outcome == Decision.ASK


def test_explicit_human_deny_has_precedence_over_advisory_allow() -> None:
    decision = compose_policy_decision(
        CommandDecision(Decision.ALLOW, "core guardrails passed", "core"),
        [CommandDecision(Decision.ALLOW, "looks safe", "plugin")],
        human_denied=True,
    )
    assert decision == CommandDecision(
        Decision.DENY, "explicitly denied by the user", "human"
    )


def test_core_sandbox_decision_cannot_be_promoted_to_unsandboxed_allow() -> None:
    core = CommandDecision(Decision.SANDBOX, "sandbox required", "core", True)
    decision = compose_policy_decision(
        core, [CommandDecision(Decision.ALLOW, "looks safe", "plugin")]
    )
    assert decision == core


def test_advisory_analyzer_timeout_requests_human_approval() -> None:
    def slow_analyzer(command: str) -> CommandDecision:
        time.sleep(0.1)
        return CommandDecision(Decision.ALLOW, "safe", "slow")

    decisions = evaluate_advisory_analyzers(
        "echo hello", [("slow", slow_analyzer)], timeout_seconds=0.01
    )
    assert decisions[0].outcome == Decision.ASK
    assert "timed out" in decisions[0].reason


def test_advisory_analyzer_failure_requests_human_approval() -> None:
    def broken_analyzer(command: str) -> CommandDecision:
        raise RuntimeError("backend unavailable")

    decisions = evaluate_advisory_analyzers(
        "echo hello", [("broken", broken_analyzer)], timeout_seconds=1
    )
    assert decisions[0].outcome == Decision.ASK
    assert "failed" in decisions[0].reason


def test_malformed_advisory_result_requests_human_approval() -> None:
    def malformed_analyzer(command: str) -> Any:
        return "allow"

    decisions = evaluate_advisory_analyzers(
        "echo hello", [("malformed", malformed_analyzer)], timeout_seconds=1
    )
    assert decisions[0].outcome == Decision.ASK


def test_llm_analyzer_adapts_injected_classifier_without_credentials() -> None:
    seen: list[str] = []

    def classifier(command: str) -> dict[str, str]:
        seen.append(command)
        return {"decision": "allow", "reason": "read-only"}

    analyzer = LLMAnalyzer(classifier, evaluator="test-llm")
    decision = analyzer("printf hello")
    assert decision == CommandDecision(Decision.ALLOW, "read-only", "test-llm")
    assert seen == ["printf hello"]


@pytest.mark.parametrize("classification", ["sandbox", {"decision": "sandbox"}])
def test_llm_analyzer_cannot_select_sandbox(classification: object) -> None:
    def classifier(command: str) -> Any:
        return classification

    with pytest.raises(ValueError, match="cannot select sandbox"):
        LLMAnalyzer(classifier)("echo hello")


def test_llm_analyzer_rejects_unknown_decision() -> None:
    with pytest.raises(ValueError, match="unsupported LLM decision"):
        LLMAnalyzer(lambda command: {"decision": "maybe"})("echo hello")


def test_firejail_argv_is_not_shell_interpolated() -> None:
    backend = FirejailBackend("/usr/bin/firejail")
    argv = backend.build_argv("printf '%s' 'hello; touch /tmp/nope'", Path("/repo"))
    assert argv[:4] == [
        "/usr/bin/firejail",
        "--quiet",
        "--private=/repo",
        "--env=HOME=/tmp",
    ]
    assert argv[-4:] == ["--", "/bin/sh", "-lc", "printf '%s' 'hello; touch /tmp/nope'"]


@pytest.mark.parametrize(
    ("network", "network_flag", "network_isolation"),
    [("none", "--net=none", True), ("host", None, False)],
)
def test_firejail_argv_applies_network_policy(
    network: Literal["none", "host"], network_flag: str | None, network_isolation: bool
) -> None:
    backend = FirejailBackend("/usr/bin/firejail", network=network)
    argv = backend.build_argv("printf hello", Path("/repo"))

    if network_flag is None:
        assert "--net=none" not in argv
    else:
        assert argv[4] == network_flag
    assert backend.capabilities().network_isolation is network_isolation


def test_bubblewrap_argv_mounts_only_writable_worktree() -> None:
    backend = BubblewrapBackend("/usr/bin/bwrap")
    argv = backend.build_argv("printf '%s' 'hello'", Path("/repo"))
    assert argv[:17] == [
        "/usr/bin/bwrap",
        "--die-with-parent",
        "--new-session",
        "--ro-bind",
        "/",
        "/",
        "--bind",
        "/repo",
        "/repo",
        "--tmpfs",
        "/tmp",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--chdir",
        "/repo",
    ]
    assert "--unshare-net" in argv
    assert argv[-4:] == ["--", "/bin/sh", "-lc", "printf '%s' 'hello'"]


@pytest.mark.parametrize(
    ("network", "network_flag", "network_isolation"),
    [("none", "--unshare-net", True), ("host", None, False)],
)
def test_bubblewrap_argv_applies_network_policy(
    network: Literal["none", "host"], network_flag: str | None, network_isolation: bool
) -> None:
    backend = BubblewrapBackend("/usr/bin/bwrap", network=network)
    argv = backend.build_argv("printf hello", Path("/repo"))

    if network_flag is None:
        assert "--unshare-net" not in argv
    else:
        assert argv[20] == network_flag
    assert backend.capabilities().network_isolation is network_isolation


def test_auto_prefers_bubblewrap_when_available() -> None:
    config = BashToolConfig.model_validate({"safety": {"sandbox": "auto"}})
    tool = Bash(config_getter=lambda: config, state=BaseToolState())
    backend = tool._sandbox_backend()
    if backend is not None:
        assert isinstance(backend, BubblewrapBackend)


def test_safety_config_round_trips_and_validates() -> None:
    config = BashToolConfig.model_validate({
        "safety": {"sandbox": "auto", "fallback": "unsandboxed"}
    })
    assert config.safety.sandbox == "auto"
    assert config.safety.fallback == "unsandboxed"
    with pytest.raises(ValueError):
        BashToolConfig.model_validate({"safety": {"sandbox": "unsafe"}})
    with pytest.raises(ValueError):
        BashToolConfig.model_validate({"safety": {"network": "project"}})


def test_unavailable_sandbox_requires_approval_by_default() -> None:
    config = BashToolConfig.model_validate({
        "safety": {"sandbox": "required", "sandbox_backend": "none"}
    })
    tool = Bash(config_getter=lambda: config, state=BaseToolState())
    permission = tool.resolve_permission(BashArgs(command="echo hello"))
    assert permission is not None
    assert permission.permission == ToolPermission.ASK
