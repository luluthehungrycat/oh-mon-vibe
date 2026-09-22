from __future__ import annotations

from pathlib import Path

import pytest

from vibe.core.plugins.lifecycle import PluginLifecycle
from vibe.core.plugins.package import (
    PluginPackage,
    PluginPackageManifest,
    PluginPackageRegistry,
)
from vibe.core.plugins.policy import PluginPermissionPolicy, PluginPermissionRule
from vibe.core.plugins.runtime import (
    PluginPermissionDenied,
    PluginRuntimeManager,
    load_package_entrypoint,
)


def _package(root: Path, entrypoint: str = "plugin:create") -> PluginPackage:
    return PluginPackage(
        PluginPackageManifest(
            schema_version="omv.plugin.v1",
            name="demo",
            version="1.0.0",
            kind="analyzer",
            entrypoint=entrypoint,
            activation="manual",
            trust="trusted_in_process",
        ),
        root,
    )


def test_enabled_entrypoint_loader_executes_only_explicit_package(
    tmp_path: Path,
) -> None:
    package = _package(tmp_path)
    (tmp_path / "plugin.py").write_text(
        "class Plugin:\n"
        "    def on_activate(self):\n"
        "        pass\n"
        "def create():\n"
        "    return Plugin()\n"
    )

    implementation = load_package_entrypoint(package)

    assert type(implementation).__name__ == "Plugin"


@pytest.mark.asyncio
async def test_denied_plugin_action_does_not_invoke_callback(tmp_path: Path) -> None:
    package = _package(tmp_path)
    (tmp_path / "plugin.py").write_text(
        "class Plugin:\n"
        "    def __init__(self):\n"
        "        self.called = False\n"
        "    async def on_activate(self):\n"
        "        pass\n"
        "    def invoke(self):\n"
        "        self.called = True\n"
        "def create():\n"
        "    return Plugin()\n"
    )
    registry = PluginPackageRegistry(enabled={"demo": package})
    lifecycle = PluginLifecycle()
    manager = PluginRuntimeManager(
        registry,
        lifecycle,
        PluginPermissionPolicy((PluginPermissionRule("deny", plugin="demo"),)),
    )
    await manager.activate_enabled()

    with pytest.raises(PluginPermissionDenied):
        await manager.invoke_authorized(
            "demo",
            "invoke",
            capability="tool",
            action="write",
            command="rm file",
            side_effect=True,
        )

    assert not vars(lifecycle.runtimes["demo"].implementation).get("called")


@pytest.mark.asyncio
async def test_runtime_manager_isolates_entrypoint_load_failure(tmp_path: Path) -> None:
    package = _package(tmp_path)
    (tmp_path / "plugin.py").write_text("raise RuntimeError('startup failed')")
    registry = PluginPackageRegistry(enabled={"demo": package})
    lifecycle = PluginLifecycle()

    await PluginRuntimeManager(registry, lifecycle).activate_enabled()

    assert lifecycle.diagnostics[-1].event == "registration_failed"
    assert "startup failed" in lifecycle.diagnostics[-1].reason


@pytest.mark.asyncio
async def test_auto_sandbox_refuses_missing_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package(tmp_path)
    registry = PluginPackageRegistry(enabled={"demo": package})
    lifecycle = PluginLifecycle()
    monkeypatch.setattr(
        "vibe.core.plugins.runtime.select_plugin_sandbox", lambda *args, **kwargs: None
    )

    await PluginRuntimeManager(
        registry, lifecycle, sandbox_policy="auto"
    ).activate_enabled()

    assert lifecycle.diagnostics[-1].event == "registration_failed"
    assert "backend is unavailable" in lifecycle.diagnostics[-1].reason
