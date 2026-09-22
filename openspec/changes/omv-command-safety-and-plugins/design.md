# Design: Oh My Vibe command safety and plugins

## Architecture

### Plugin contract

Add `vibe/core/plugins/` with small public models:

- `PluginManifest(name, version, api_version, kind, capabilities)`
- `PluginContext` exposing read-only configuration and registration methods
- `PluginRegistry` for policy analyzers, sandbox backends, and lifecycle hooks
- `discover_plugins()` using `importlib.metadata.entry_points(group="omv.plugins")`

Plugins expose a `register(registry)` callable and a manifest. The registry validates API compatibility, applies the configured enabled-plugin allowlist, and catches failures per plugin. The contract deliberately avoids importing internal AgentLoop classes so it can later move to a standalone package.

### Command policy

Add `vibe/core/safety/` with a pure policy layer. The existing Bash guardrail analysis remains authoritative. A `CommandDecision` carries outcome, reason, evaluator, and sandbox eligibility. The policy combines decisions in this order:

1. Built-in deny rules and explicit human deny.
2. Path and capability checks.
3. Plugin analyzers, including an optional LLM analyzer, as advisory inputs.
4. Sandbox selection for eligible commands.
5. Human approval for ambiguity or unsafe fallback.

The initial implementation includes the protocol and deterministic evaluator. The LLM evaluator is a plugin contract with a timeout and no permission to override core deny decisions; provider-specific adapters can be added without changing Bash.

### Sandbox runner

Add a `SandboxBackend` protocol with Linux Bubblewrap and Firejail implementations. Bubblewrap is preferred when `auto` detects it; Firejail remains an explicit or secondary backend. Backends build argv lists rather than shell strings, run with the project directory as the writable scope, support the explicit network modes `none` and `host`, and report startup failures separately from command exit codes. `none` is the default and disables network access; `host` explicitly keeps host networking. A project-scoped network mode is unsupported until a backend exposes a real network-scope primitive. The default mode is `off` for compatibility. When enabled, sandbox startup failure defaults to `ask` before unsandboxed fallback.

The Bash tool will ask the safety runtime for an execution plan. The plan selects the existing terminal transport when available or the local subprocess path, while preserving existing timeout, output limits, and cancellation behavior.

### Configuration

Extend the tool configuration with a nested `safety` section:

- `sandbox`: `off`, `auto`, or `required`
- `sandbox_backend`: `auto`, `bubblewrap`, `firejail`, or `none`
- `network`: `none` or `host`; `project` is unsupported until a backend provides a project-scoped network primitive
- `fallback`: `ask`, `deny`, or `unsandboxed`
- `policy`: `deterministic`, `hybrid`, or `plugin`
- `llm_timeout_seconds`
- `enabled_plugins`

Defaults preserve current behavior: sandbox `off`, deterministic policy, and no LLM calls.

## Security decisions

- No plugin can weaken a built-in deny decision.
- No automatic unsandboxed fallback is allowed by default.
- LLM output is untrusted data and is advisory only.
- Plugin loading is explicit and failure-isolated.
- Sandbox command construction uses argv; user commands remain interpreted by the configured shell inside the sandbox, but backend arguments are never assembled through shell interpolation.
- Network access is disabled by default when sandboxing is enabled.

## Alternatives considered

- **Docker/Podman per command:** stronger isolation but high startup cost, dependency burden, UID/mount complexity, and poor interactive command support. Keep as a future backend.
- **Firejail only with no abstraction:** fast to implement but prevents later extraction and makes other platforms difficult. Use a backend protocol with Bubblewrap preferred on Linux and Firejail as a secondary implementation.
- **LLM-only approval:** rejected because model classifiers can be manipulated and are poor at proving filesystem/process effects. Keep deterministic guardrails authoritative.
- **Silent fallback to host execution:** rejected because a failed sandbox is precisely when the safety guarantee is unavailable.

## Migration and rollback

The default configuration is unchanged. Users can enable sandboxing incrementally in `config.toml`. Removing the safety configuration returns to current execution behavior. Plugin packages remain optional and are not bundled into the core distribution.

## Non-goals

- Full operating-system security guarantees against a privileged host compromise.
- Automatically approving arbitrary commands based only on an LLM.
- Replacing the existing permission UI or permission store in this change.
- Shipping a Docker backend in the first implementation.
