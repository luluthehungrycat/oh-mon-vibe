from __future__ import annotations

from vibe.core.config import PluginConfig, VibeConfigSchema


def test_plugin_configuration_is_disabled_and_unsandboxed_by_default() -> None:
    config = VibeConfigSchema()
    assert config.plugins == PluginConfig()
    assert config.plugins.enabled == []
    assert config.plugins.sandbox == "off"


def test_plugin_configuration_accepts_granular_rules_and_required_sandbox() -> None:
    config = VibeConfigSchema.model_validate({
        "plugins": {
            "enabled": ["trusted"],
            "sandbox": "required",
            "sandbox_backend": "bubblewrap",
            "permissions": [
                {
                    "plugin": "trusted",
                    "capability": "tool",
                    "action": "read",
                    "command": "cat *",
                    "outcome": "always",
                }
            ],
        }
    })
    assert config.plugins.enabled == ["trusted"]
    assert config.plugins.sandbox == "required"
    assert config.plugins.permissions[0].outcome == "always"
    policy = config.plugins.permission_policy()
    assert policy.rules[0].outcome == "always"
