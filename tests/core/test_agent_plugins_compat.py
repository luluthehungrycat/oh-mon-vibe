from __future__ import annotations

import json
from pathlib import Path

from vibe.core.plugins import PluginResolver


def test_agent_plugins_package_uses_standard_files_and_ignores_omv_extension(
    tmp_path: Path,
) -> None:
    package = tmp_path / "demo"
    (package / "skills" / "guide").mkdir(parents=True)
    (package / "plugin.json").write_text(
        json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "demo",
            "version": "1.0.0",
            "extensions": {
                "com.ohmyvibe": {"capabilities": ["native_tool", "hook", "sandbox"]}
            },
        }),
        encoding="utf-8",
    )
    (package / "mcp.json").write_text(
        json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {"sample": {"type": "stdio", "command": "sample-mcp"}},
        }),
        encoding="utf-8",
    )
    (package / "skills" / "guide" / "SKILL.md").write_text(
        "---\nname: guide\ndescription: A sample guide skill\n---\nUse this guide.\n",
        encoding="utf-8",
    )

    resolved = PluginResolver(project_roots=[tmp_path]).resolve()

    assert [plugin.name for plugin in resolved.plugins] == ["demo"]
    assert resolved.skills
    assert [server.source_id for server in resolved.mcp_servers] == ["sample"]
    assert resolved.runtime_hooks == ()
    assert resolved.libraries == ()
    assert resolved.connectors == ()
    assert resolved.issues == ()


def test_omv_v1_manifest_is_not_a_supported_package_format(tmp_path: Path) -> None:
    package = tmp_path / "legacy"
    package.mkdir()
    (package / "plugin.json").write_text(
        json.dumps({
            "$schema": "omv.plugin.v1",
            "name": "legacy",
            "version": "1.0.0",
            "capabilities": ["tool", "hook", "sandbox"],
        }),
        encoding="utf-8",
    )

    resolved = PluginResolver(project_roots=[tmp_path]).resolve()

    assert resolved.plugins == ()
    assert resolved.skills == {}
    assert resolved.mcp_servers == ()
    assert [issue.code for issue in resolved.issues] == [
        "plugin.compatibility.format_unrecognized"
    ]


def test_malformed_mcp_json_records_a_diagnostic(tmp_path: Path) -> None:
    package = tmp_path / "demo"
    package.mkdir()
    (package / "plugin.json").write_text(
        json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "demo",
            "version": "1.0.0",
        }),
        encoding="utf-8",
    )
    mcp_config = package / "mcp.json"
    mcp_config.write_text("{", encoding="utf-8")

    resolved = PluginResolver(project_roots=[tmp_path]).resolve()

    assert [plugin.name for plugin in resolved.plugins] == ["demo"]
    assert resolved.mcp_servers == ()
    assert any(
        issue.file == mcp_config
        and issue.message.startswith("Failed to load MCP configuration:")
        for issue in resolved.issues
    )
