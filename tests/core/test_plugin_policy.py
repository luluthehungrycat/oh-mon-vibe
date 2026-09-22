from __future__ import annotations

from vibe.core.plugins.policy import (
    PluginAnalyzerResult,
    PluginDecision,
    PluginPermissionPolicy,
    PluginPermissionRule,
    compose_plugin_decision,
)
from vibe.core.safety.policy import CommandDecision, Decision


def test_safe_read_only_plugin_action_is_auto_allowed() -> None:
    result = PluginPermissionPolicy().analyze(
        plugin="reader",
        capability="analyzer",
        action="inspect",
        command="git diff",
        side_effect=False,
    )
    assert result.decision == PluginDecision.ALLOW


def test_plugin_side_effect_defaults_to_approval() -> None:
    result = PluginPermissionPolicy().analyze(
        plugin="writer",
        capability="tool",
        action="write",
        command="rm file",
        side_effect=True,
    )
    assert result.decision == PluginDecision.ASK


def test_specific_plugin_rule_overrides_wildcard_rule() -> None:
    policy = PluginPermissionPolicy((
        PluginPermissionRule("deny", plugin="*", capability="tool"),
        PluginPermissionRule(
            "always", plugin="trusted", capability="tool", action="read"
        ),
    ))
    result = policy.analyze(
        plugin="trusted",
        capability="tool",
        action="read",
        command="cat file",
        side_effect=False,
    )
    assert result.decision == PluginDecision.ALLOW


def test_conflicting_equally_specific_rules_request_approval() -> None:
    policy = PluginPermissionPolicy((
        PluginPermissionRule("always", plugin="demo", action="write"),
        PluginPermissionRule("deny", plugin="demo", action="write"),
    ))
    result = policy.analyze(
        plugin="demo",
        capability="tool",
        action="write",
        command="write file",
        side_effect=True,
    )
    assert result.decision == PluginDecision.ASK


def test_core_dangerous_command_denial_cannot_be_overridden() -> None:
    core = CommandDecision(Decision.DENY, "deterministic guardrail denial", "core")
    decision = compose_plugin_decision(
        core,
        PluginAnalyzerResult(PluginDecision.ALLOW, "plugin says safe"),
        plugin="demo",
    )
    assert decision.outcome == Decision.DENY
    assert decision.reason == "deterministic guardrail denial"


def test_human_denial_has_precedence_over_plugin_allow() -> None:
    decision = compose_plugin_decision(
        CommandDecision(Decision.ALLOW, "safe", "core"),
        PluginAnalyzerResult(PluginDecision.ALLOW, "plugin says safe"),
        plugin="demo",
        human_denied=True,
    )
    assert decision.outcome == Decision.DENY
