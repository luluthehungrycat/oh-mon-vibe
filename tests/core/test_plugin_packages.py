from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibe.core.plugins import (
    PluginPackageManifest,
    add_legacy_entrypoint_diagnostics,
    discover_package_plugins,
)


def _write_manifest(root: Path, **overrides: object) -> Path:
    package = root / str(overrides.get("name", "demo"))
    package.mkdir(parents=True)
    manifest = {
        "schema": "omv.plugin.v1",
        "name": "demo",
        "version": "1.0.0",
        "kind": "analyzer",
        "capabilities": [],
        "entrypoint": "plugin:register",
        "activation": "manual",
        "trust": "trusted_in_process",
        "sandbox": "optional",
    }
    manifest.update(overrides)
    (package / "plugin.json").write_text(json.dumps(manifest))
    return package


def test_valid_package_is_enabled_only_when_allowlisted(tmp_path: Path) -> None:
    _write_manifest(tmp_path)

    disabled = discover_package_plugins(set(), global_root=tmp_path)
    enabled = discover_package_plugins({"demo"}, global_root=tmp_path)

    assert list(disabled.installed) == ["demo"]
    assert disabled.enabled == {}
    assert disabled.diagnostics[0].event == "disabled"
    assert list(enabled.enabled) == ["demo"]


def test_package_discovery_does_not_import_entrypoint(tmp_path: Path) -> None:
    package = _write_manifest(tmp_path)
    (package / "plugin.py").write_text("raise AssertionError('must not import')")

    registry = discover_package_plugins({"demo"}, global_root=tmp_path)

    assert list(registry.enabled) == ["demo"]


@pytest.mark.parametrize(
    ("field", "value"), [("schema", "omv.plugin.v2"), ("trust", "isolated_process")]
)
def test_package_discovery_rejects_unsupported_manifest_values(
    tmp_path: Path, field: str, value: str
) -> None:
    _write_manifest(tmp_path, **{field: value})

    registry = discover_package_plugins({"demo"}, global_root=tmp_path)

    assert registry.installed == {}


def test_package_discovery_rejects_duplicate_names(tmp_path: Path) -> None:
    global_root = tmp_path / "global"
    project_root = tmp_path / "project"
    _write_manifest(global_root)
    _write_manifest(project_root / ".omv" / "plugins", name="demo")

    registry = discover_package_plugins(
        {"demo"}, global_root=global_root, project_root=project_root
    )

    assert list(registry.installed) == ["demo"]
    assert registry.diagnostics[-1].event == "duplicate"


def test_fixed_components_load_without_importing_plugin_code(tmp_path: Path) -> None:
    package = _write_manifest(tmp_path, capabilities=["skills", "mcp"])
    (package / "skills").mkdir()
    (package / "mcp.json").write_text(json.dumps({"servers": []}))

    registry = discover_package_plugins({"demo"}, global_root=tmp_path)

    components = registry.components["demo"]
    assert components.skills == package / "skills"
    assert components.mcp == {"servers": []}
    assert components.diagnostics == ()


def test_component_failure_does_not_hide_other_components(tmp_path: Path) -> None:
    package = _write_manifest(tmp_path, capabilities=["skills", "mcp"])
    (package / "skills").mkdir()
    (package / "mcp.json").write_text("{")

    registry = discover_package_plugins({"demo"}, global_root=tmp_path)

    components = registry.components["demo"]
    assert components.skills == package / "skills"
    assert components.mcp is None
    assert registry.diagnostics[-1].event == "component_rejected"


def test_legacy_entrypoint_diagnostic_does_not_enable_package() -> None:
    registry = discover_package_plugins(set())

    add_legacy_entrypoint_diagnostics(registry, ["legacy"])

    assert registry.enabled == {}
    assert registry.diagnostics[-1].event == "legacy_entrypoint"


def test_package_discovery_rejects_symlinked_components(tmp_path: Path) -> None:
    package = _write_manifest(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (package / "skills").symlink_to(outside, target_is_directory=True)

    registry = discover_package_plugins({"demo"}, global_root=tmp_path)

    assert registry.installed == {}
    assert registry.diagnostics[-1].event == "manifest_rejected"


def test_manifest_requires_semantic_version_and_safe_entrypoint() -> None:
    with pytest.raises(ValueError):
        PluginPackageManifest(
            name="demo", version="latest", kind="analyzer", entrypoint="plugin:register"
        )
    with pytest.raises(ValueError):
        PluginPackageManifest(
            name="demo",
            version="1.0.0",
            kind="analyzer",
            entrypoint="../plugin:register",
        )
