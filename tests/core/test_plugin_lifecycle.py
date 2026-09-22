from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Literal

import pytest

from vibe.core.plugins.lifecycle import PluginLifecycle, PluginLifecyclePhase
from vibe.core.plugins.package import PluginPackage, PluginPackageManifest


def _package(*, sandbox: Literal["optional", "required"] = "optional") -> PluginPackage:
    manifest = PluginPackageManifest(
        name="demo",
        version="1.0.0",
        kind="analyzer",
        entrypoint="plugin:register",
        sandbox=sandbox,
    )
    return PluginPackage(manifest, Path("/tmp/demo"))


@pytest.mark.asyncio
async def test_lifecycle_isolates_activation_failure() -> None:
    class Broken:
        async def on_activate(self) -> None:
            raise RuntimeError("broken")

    lifecycle = PluginLifecycle()
    assert await lifecycle.activate(_package(), Broken()) is False
    assert lifecycle.runtimes["demo"].phase == PluginLifecyclePhase.FAILED
    assert lifecycle.diagnostics[-1].event == "activation_failed"


@pytest.mark.asyncio
async def test_lifecycle_bounds_slow_async_callback() -> None:
    class Slow:
        async def on_activate(self) -> None:
            await asyncio.sleep(0.05)

    package = PluginPackage(
        _package().manifest.model_copy(update={"lifecycle_timeout_seconds": 0.01}),
        Path("/tmp/demo"),
    )
    lifecycle = PluginLifecycle()
    assert await lifecycle.activate(package, Slow()) is False
    assert lifecycle.diagnostics[-1].event == "activation_failed"


@pytest.mark.asyncio
async def test_required_sandbox_refuses_activation_without_backend() -> None:
    lifecycle = PluginLifecycle(sandbox_available=False)
    assert await lifecycle.activate(_package(sandbox="required"), object()) is False
    assert lifecycle.runtimes["demo"].phase == PluginLifecyclePhase.FAILED
    assert lifecycle.diagnostics[-1].event == "sandbox_required"


@pytest.mark.asyncio
async def test_lifecycle_deactivation_runs_cleanup_and_stops() -> None:
    class Plugin:
        def __init__(self) -> None:
            self.deactivated = False

        async def on_deactivate(self) -> None:
            self.deactivated = True

    plugin = Plugin()
    lifecycle = PluginLifecycle()
    assert await lifecycle.activate(_package(), plugin)
    assert await lifecycle.deactivate("demo")
    assert plugin.deactivated
    assert lifecycle.runtimes["demo"].phase == PluginLifecyclePhase.STOPPED
