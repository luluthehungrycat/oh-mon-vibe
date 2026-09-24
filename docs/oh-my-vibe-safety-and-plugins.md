# Oh My Vibe: why the prefix is earned

Oh My Vibe is not only a renamed Mistral Vibe distribution. Its current differentiators are:

- **Durable, inspectable memory** under `~/.omv`.
- **Self-writing skills** with explicit configuration and regression coverage.
- **Safe coexistence** with vanilla Vibe through `omv`/`omv-acp` and isolated state.
- **Controlled upstream synchronization** with compatibility checks, review branches, and gated releases.
- **Lower approval fatigue** through optional sandboxed Bash execution and advisory policy analyzers.

## Safety configuration

The default remains compatible with existing behavior:

```toml
[tools.bash.safety]
sandbox = "off"          # off, auto, required
sandbox_backend = "auto" # auto, bubblewrap, firejail, none
network = "none"         # none, host
fallback = "ask"         # ask, deny, unsandboxed
policy = "deterministic" # deterministic, hybrid, plugin
llm_timeout_seconds = 5
enabled_plugins = []
```

For a Linux host with Bubblewrap installed, an opt-in setup is:

```toml
[tools.bash.safety]
sandbox = "auto"
sandbox_backend = "bubblewrap"
network = "none"
fallback = "ask"
```

Commands that pass core guardrails can run in the project sandbox without a repeated approval prompt. Bubblewrap uses a read-only host view, a writable project worktree, private `/tmp`, isolated `/proc` and `/dev`, and the configured network mode: `none` disables network access, while `host` explicitly keeps host networking. `project` is unsupported because neither backend currently provides a project-scoped network primitive. Firejail remains available as a secondary backend. If the selected backend cannot start, `ask` requires approval before the command falls back to the host. `deny` never falls back; `unsandboxed` is available only as an explicit user choice.

## Agent Plugins

Oh My Vibe follows the upstream Agent Plugins 1.0 package contract: a `plugin.json` at the package root, an optional fixed `skills/` directory, and an optional root `mcp.json` using the published Agent Plugins MCP schema. User packages are discovered below `~/.omv/plugins/`; project packages are discovered below `.vibe/plugins/`.

There is no OMV-owned root manifest or `omv.plugin.v1` schema. OMV-specific metadata belongs under the stable reverse-domain key `extensions["com.ohmyvibe"]`. The namespace currently defines no executable capabilities and is inert. The current OMV v1 package claim is standard Agent Plugins skills/MCP plus upstream discovery and inspection. OMV-native analyzers, tools, hooks, and plugin-specific sandbox enforcement are deferred. The existing Python analyzer entry-point registry is a separate internal Bash safety extension; it does not load Agent Plugins packages. MCP server authorization and tool permissions follow Vibe's existing behavior.

## Internal Python analyzer entry points

The `omv.plugins` Python entry-point group is an internal, trusted-process Bash safety extension, not an Agent Plugins package format. Plugins are explicitly selected through `tools.bash.safety.enabled_plugins` and can return advisory command decisions. They cannot override core Bash deny rules or explicit human denials. Sandbox-backend registration remains metadata-only; Bash does not execute registry-provided backends.

An analyzer result may be `allow`, `deny`, or `ask`; timeouts, exceptions, malformed results, and ambiguous decisions request human approval rather than automatic approval. The core project does not select an LLM provider or read credentials for this path. The optional `LLMAnalyzer` adapter accepts an injected classifier callable.

## Bash policy and sandbox boundary

Core Bash guardrails remain authoritative. A deterministic deny cannot be changed by a plugin or model analyzer. An explicit human denial is represented as a denial from the `human` evaluator. Advisory analyzer results may deny or request approval, but an `allow` result cannot promote a command that core policy requires to run in a sandbox. Sandbox selection and fallback policy determine whether an eligible command runs sandboxed or requires approval.

Timeouts bound the caller's wait, but a Python thread that is already running cannot be forcibly stopped. Analyzer implementations should therefore be trusted, short-lived callables; untrusted or potentially blocking integrations require a separately isolated process boundary.

Bash results expose structured `policy_mode`, `evaluator`, `sandboxed`, `sandbox_backend`, `fallback_applied`, and `fallback_reason` fields. The Bash result display includes the policy, evaluator, sandbox state, and backend so an automatic approval is inspectable without parsing free-form notes. Managed terminal transport is rejected whenever sandbox policy is enabled and is only delegated after the same core permission check used by local execution; it is not treated as a sandbox substitute.

This change intentionally does not complete the separate branding-compliance migration tracked by issue #2. The safety PR preserves the existing package and executable identity; the branding migration must be reviewed independently before release.

## Skill portability

Oh My Vibe-specific skills should be kept portable when possible. Use `.agents/skills/` for harness-agnostic skills. Use `.opencode/skills/`, `.codex/skills/`, `.pi/skills/`, `.claude/skills/`, or `.vibe/skills/` only for harness-specific variants. Hermes-global skills are copied into the repository only when they are directly specific to Oh My Vibe.
