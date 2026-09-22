"""Host-owned plugin analyzer and granular permission decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fnmatch import fnmatchcase
from typing import Literal

from vibe.core.safety.policy import CommandDecision, Decision, compose_policy_decision


class PluginDecision(StrEnum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


PluginRuleOutcome = Literal["always", "ask", "deny"]


@dataclass(frozen=True)
class PluginAnalyzerResult:
    decision: PluginDecision
    reason: str
    sandbox_eligible: bool = False

    def as_command_decision(self, plugin: str) -> CommandDecision:
        return CommandDecision(
            Decision(self.decision.value), self.reason, plugin, self.sandbox_eligible
        )


@dataclass(frozen=True)
class PluginPermissionRule:
    outcome: PluginRuleOutcome
    plugin: str = "*"
    capability: str = "*"
    action: str = "*"
    command: str = "*"

    def matches(
        self, *, plugin: str, capability: str, action: str, command: str
    ) -> bool:
        return all(
            fnmatchcase(value, pattern)
            for value, pattern in (
                (plugin, self.plugin),
                (capability, self.capability),
                (action, self.action),
                (command, self.command),
            )
        )

    def specificity(self) -> int:
        return sum(
            value != "*"
            for value in (self.plugin, self.capability, self.action, self.command)
        )


@dataclass(frozen=True)
class PluginPermissionPolicy:
    rules: tuple[PluginPermissionRule, ...] = ()

    def analyze(
        self,
        *,
        plugin: str,
        capability: str,
        action: str,
        command: str,
        side_effect: bool,
    ) -> PluginAnalyzerResult:
        matches = [
            rule
            for rule in self.rules
            if rule.matches(
                plugin=plugin, capability=capability, action=action, command=command
            )
        ]
        if not matches:
            if side_effect:
                return PluginAnalyzerResult(
                    PluginDecision.ASK,
                    "plugin side effect requires approval by default",
                )
            return PluginAnalyzerResult(PluginDecision.ALLOW, "read-only plugin action")
        highest = max(rule.specificity() for rule in matches)
        selected = [rule for rule in matches if rule.specificity() == highest]
        outcomes = {rule.outcome for rule in selected}
        if len(outcomes) != 1:
            return PluginAnalyzerResult(
                PluginDecision.ASK,
                "conflicting plugin permission rules require approval",
            )
        outcome = selected[0].outcome
        if outcome == "deny":
            return PluginAnalyzerResult(
                PluginDecision.DENY, "denied by plugin permission rule"
            )
        if outcome == "ask":
            return PluginAnalyzerResult(
                PluginDecision.ASK, "approval required by plugin permission rule"
            )
        return PluginAnalyzerResult(
            PluginDecision.ALLOW, "allowed by plugin permission rule"
        )


def compose_plugin_decision(
    core: CommandDecision,
    result: PluginAnalyzerResult,
    *,
    plugin: str,
    human_denied: bool = False,
) -> CommandDecision:
    """Apply host guardrails and explicit human precedence to plugin output."""
    return compose_policy_decision(
        core, [result.as_command_decision(plugin)], human_denied=human_denied
    )
