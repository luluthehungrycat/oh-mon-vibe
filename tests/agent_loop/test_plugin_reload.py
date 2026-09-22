from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.conftest import (
    build_test_agent_loop,
    build_test_vibe_config,
    set_agent_config,
)
from vibe.core.config import PluginConfig
from vibe.core.plugins.lifecycle import PluginLifecyclePhase


def _write_plugin(project_root: Path) -> None:
    package = project_root / ".omv" / "plugins" / "demo"
    package.mkdir(parents=True)
    (package / "plugin.json").write_text(
        json.dumps({
            "schema": "omv.plugin.v1",
            "name": "demo",
            "version": "1.0.0",
            "kind": "tool",
            "capabilities": ["tool"],
            "entrypoint": "plugin:create",
            "activation": "manual",
            "trust": "trusted_in_process",
        })
    )
    (package / "plugin.py").write_text(
        """
class Plugin:
    async def register(self):
        pass

    async def on_activate(self):
        pass

    async def on_deactivate(self):
        pass

    async def cleanup(self):
        pass


def create():
    return Plugin()
"""
    )


@pytest.mark.asyncio
async def test_reload_reconciles_plugin_enablement(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_plugin(tmp_path)
    agent = build_test_agent_loop(config=build_test_vibe_config(plugins=PluginConfig()))
    try:
        await agent.wait_until_ready()
        assert agent.plugin_package_registry.enabled == {}

        enabled_config = build_test_vibe_config(plugins=PluginConfig(enabled=["demo"]))
        previous_lifecycle = agent.plugin_lifecycle
        set_agent_config(agent, enabled_config)
        await agent.reload_with_initial_messages()

        active_lifecycle = agent.plugin_lifecycle
        assert list(agent.plugin_package_registry.enabled) == ["demo"]
        assert active_lifecycle.runtimes, active_lifecycle.diagnostics
        assert active_lifecycle.runtimes["demo"].phase is PluginLifecyclePhase.ACTIVATE

        disabled_config = build_test_vibe_config(plugins=PluginConfig())
        set_agent_config(agent, disabled_config)
        await agent.reload_with_initial_messages()

        assert previous_lifecycle.runtimes == {}
        assert active_lifecycle.runtimes["demo"].phase is PluginLifecyclePhase.STOPPED
        assert agent.plugin_package_registry.enabled == {}
        assert agent.plugin_lifecycle.runtimes == {}
        assert agent._active_plugin_skill_paths == ()
    finally:
        await agent.aclose()
