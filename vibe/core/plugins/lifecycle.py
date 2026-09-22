"""Bounded, failure-isolated lifecycle management for enabled plugins."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum, auto
from inspect import iscoroutinefunction
from typing import Any, Literal, cast

from vibe.core.plugins.package import PluginPackage


class PluginLifecyclePhase(StrEnum):
    DISCOVER = auto()
    VALIDATE = auto()
    ENABLE = auto()
    REGISTER = auto()
    ACTIVATE = auto()
    INVOKE = auto()
    DEACTIVATE = auto()
    CLEANUP = auto()
    STOPPED = auto()
    FAILED = auto()


PluginLifecycleEvent = Literal[
    "registered",
    "activated",
    "invoked",
    "deactivated",
    "cleaned_up",
    "registration_failed",
    "activation_failed",
    "invocation_failed",
    "deactivation_failed",
    "cleanup_failed",
    "sandbox_required",
]


@dataclass(frozen=True)
class PluginLifecycleDiagnostic:
    plugin: str
    event: PluginLifecycleEvent
    phase: PluginLifecyclePhase
    reason: str


@dataclass
class PluginRuntime:
    package: PluginPackage
    implementation: object
    phase: PluginLifecyclePhase = PluginLifecyclePhase.DISCOVER


@dataclass
class PluginLifecycle:
    sandbox_available: bool = False
    runtimes: dict[str, PluginRuntime] = field(default_factory=dict)
    diagnostics: list[PluginLifecycleDiagnostic] = field(default_factory=list)

    async def activate(self, package: PluginPackage, implementation: object) -> bool:
        name = package.manifest.name
        runtime = PluginRuntime(package, implementation)
        self.runtimes[name] = runtime
        runtime.phase = PluginLifecyclePhase.VALIDATE
        if package.manifest.sandbox == "required" and not self.sandbox_available:
            runtime.phase = PluginLifecyclePhase.FAILED
            self._diagnose(
                name,
                "sandbox_required",
                runtime.phase,
                "plugin requires isolation but no supported sandbox is available",
            )
            return False
        runtime.phase = PluginLifecyclePhase.ENABLE
        try:
            await self._invoke(
                implementation, "register", package.manifest.lifecycle_timeout_seconds
            )
        except Exception as exc:
            runtime.phase = PluginLifecyclePhase.FAILED
            self._diagnose(name, "registration_failed", runtime.phase, str(exc))
            return False
        runtime.phase = PluginLifecyclePhase.REGISTER
        self._diagnose(name, "registered", runtime.phase, "plugin registered")
        try:
            await self._invoke(
                implementation,
                "on_activate",
                package.manifest.lifecycle_timeout_seconds,
            )
        except Exception as exc:
            runtime.phase = PluginLifecyclePhase.FAILED
            self._diagnose(name, "activation_failed", runtime.phase, str(exc))
            return False
        runtime.phase = PluginLifecyclePhase.ACTIVATE
        self._diagnose(name, "activated", runtime.phase, "plugin activated")
        return True

    async def invoke(self, name: str, method_name: str, *args: Any) -> object:
        runtime = self.runtimes[name]
        if runtime.phase is not PluginLifecyclePhase.ACTIVATE:
            raise RuntimeError(f"plugin {name!r} is not active")
        runtime.phase = PluginLifecyclePhase.INVOKE
        try:
            result = await self._invoke(
                runtime.implementation,
                method_name,
                runtime.package.manifest.lifecycle_timeout_seconds,
                *args,
            )
        except Exception as exc:
            runtime.phase = PluginLifecyclePhase.FAILED
            self._diagnose(name, "invocation_failed", runtime.phase, str(exc))
            raise
        runtime.phase = PluginLifecyclePhase.ACTIVATE
        self._diagnose(name, "invoked", runtime.phase, method_name)
        return result

    async def deactivate(self, name: str) -> bool:
        runtime = self.runtimes.get(name)
        if runtime is None or runtime.phase is PluginLifecyclePhase.STOPPED:
            return True
        runtime.phase = PluginLifecyclePhase.DEACTIVATE
        failed = False
        try:
            await self._invoke(
                runtime.implementation,
                "on_deactivate",
                runtime.package.manifest.lifecycle_timeout_seconds,
            )
        except Exception as exc:
            failed = True
            self._diagnose(name, "deactivation_failed", runtime.phase, str(exc))
        runtime.phase = PluginLifecyclePhase.CLEANUP
        try:
            await self._invoke(
                runtime.implementation,
                "cleanup",
                runtime.package.manifest.lifecycle_timeout_seconds,
            )
        except Exception as exc:
            failed = True
            self._diagnose(name, "cleanup_failed", runtime.phase, str(exc))
        if failed:
            runtime.phase = PluginLifecyclePhase.FAILED
            return False
        runtime.phase = PluginLifecyclePhase.STOPPED
        self._diagnose(name, "deactivated", runtime.phase, "plugin deactivated")
        self._diagnose(name, "cleaned_up", runtime.phase, "plugin cleaned up")
        return True

    async def shutdown(self) -> None:
        for name in reversed(tuple(self.runtimes)):
            await self.deactivate(name)

    def record_failure(self, name: str, reason: str) -> None:
        runtime = self.runtimes.get(name)
        if runtime is not None:
            runtime.phase = PluginLifecyclePhase.FAILED
        self._diagnose(name, "registration_failed", PluginLifecyclePhase.FAILED, reason)

    def _diagnose(
        self,
        plugin: str,
        event: PluginLifecycleEvent,
        phase: PluginLifecyclePhase,
        reason: str,
    ) -> None:
        self.diagnostics.append(PluginLifecycleDiagnostic(plugin, event, phase, reason))

    @staticmethod
    async def _invoke(
        implementation: object, method_name: str, timeout: float, *args: Any
    ) -> object:
        callback = getattr(implementation, method_name, None)
        if not callable(callback):
            return None
        if not iscoroutinefunction(callback) and not iscoroutinefunction(
            type(callback).__call__
        ):
            raise TypeError("plugin lifecycle callbacks must be async")
        typed_callback = cast(Callable[..., Awaitable[object]], callback)
        return await asyncio.wait_for(typed_callback(*args), timeout)
