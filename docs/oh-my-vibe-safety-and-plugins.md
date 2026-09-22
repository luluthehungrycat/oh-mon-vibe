# Oh My Vibe: why the prefix is earned

Oh My Vibe is not only a renamed Mistral Vibe distribution. Its current differentiators are:

- **Durable, inspectable memory** under `~/.omv`.
- **Self-writing skills** with explicit configuration and regression coverage.
- **Safe coexistence** with vanilla Vibe through `omv`/`omv-acp` and isolated state.
- **Controlled upstream synchronization** with compatibility checks, review branches, and gated releases.
- **Modular safety extensions** that can eventually be extracted as a vendor-neutral plugin project.
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

## Manifest package standard

The current OMV package contract is `omv.plugin.v1` in a regular
`plugin.json` at the package root. Packages are discovered from
`~/.omv/plugins/<name>/` and `.omv/plugins/<name>/` as inert manifests; they
are installed but disabled until `plugins.enabled` explicitly names them.
Discovery never imports disabled entrypoints.

```toml
[plugins]
enabled = ["example"]
sandbox = "off"          # off, auto, required
sandbox_backend = "auto" # auto, bubblewrap, firejail

[[plugins.permissions]]
plugin = "example"
capability = "tool"
action = "read"
command = "cat *"
outcome = "always"       # always, ask, deny
```

The manifest declares semantic `version`, `kind`, `capabilities`,
package-local `entrypoint`, manual activation, trusted in-process execution,
and an optional or required sandbox expectation. `skills/` and `mcp.json` are
fixed, root-contained components and fail independently. The existing Python
entry-point registry remains an internal migration path; it is diagnosed as
legacy and never silently promoted to a package.

## Legacy Python entry-point contract

Legacy plugins are discovered from the `omv.plugins` Python entry-point group
and must be explicitly listed in `enabled_plugins`. They declare a manifest with:

- plugin name and version;
- API version;
- plugin kind (`analyzer`, `sandbox`, or `combined`);
- capabilities (`analyzer` and/or `sandbox_backend`);
- trusted in-process execution status.

Unknown capabilities, capabilities outside the declared kind, unsupported API versions, and process-isolated trust requests are rejected. Registration failures remain isolated and are exposed through structured plugin diagnostics with plugin identity, failure reason, trust level, and isolation status.

Plugins can register command analyzers and sandbox backends. Sandbox-backend registration remains metadata-only until a reviewed adapter and isolation contract exists; Bash does not silently execute registry-provided backends. Plugins cannot override built-in deny rules or silently grant themselves permission bypasses. Failures are isolated per plugin.

An LLM command analyzer can therefore be shipped as an optional plugin. Its result is advisory: `allow`, `deny`, or `ask`; timeouts and ambiguous results become human approval, and deterministic guardrails always win. The core project intentionally does not hard-code a provider or credentials into this path.

## Current boundary

The first wedge implements the public plugin contracts, Bubblewrap/Firejail backends, Bash integration, fallback semantics, analyzer composition, and structured audit metadata. Future work includes a provider-specific LLM analyzer, managed/interactive terminal integration, richer backend capability probing, and extraction of the plugin contracts into a standalone package.

## Policy precedence

The policy layer applies decisions in this order:

1. Core Bash guardrails remain authoritative. A deterministic deny cannot be changed by a plugin or model analyzer.
2. An explicit human denial is represented as a denial from the `human` evaluator.
3. Advisory analyzer results may deny or request approval, but an `allow` result cannot promote a command that core policy requires to run in a sandbox.
4. Sandbox selection and fallback policy determine whether an eligible command runs sandboxed or requires approval.

This composition is intentionally small and provider-neutral. Analyzer timeout, exceptions, malformed results, and unsupported async results become an approval request rather than an automatic allow. The timeout is bounded by `llm_timeout_seconds` and applies independently to each enabled analyzer.

Timeouts bound the caller's wait, but a Python thread that is already running cannot be forcibly stopped. Analyzer implementations should therefore be trusted, short-lived callables; untrusted or potentially blocking integrations require a separately isolated process boundary.

The optional `LLMAnalyzer` adapter accepts an injected classifier callable. Core Oh My Vibe neither selects a provider nor reads credentials for this adapter. The classifier may return `allow`, `deny`, or `ask` (as a decision value, string, or mapping); invalid output and attempts to select `sandbox` fail closed and are converted to approval requests by the analyzer runner.

Bash results now expose structured `policy_mode`, `evaluator`, `sandboxed`, `sandbox_backend`, `fallback_applied`, and `fallback_reason` fields. The Bash result display includes the policy, evaluator, sandbox state, and backend so an automatic approval is inspectable without parsing free-form notes. Managed terminal transport is rejected whenever sandbox policy is enabled and is only delegated after the same core permission check used by local execution; it is not treated as a sandbox substitute.

This change intentionally does not complete the separate branding-compliance migration tracked by issue #2. The safety PR preserves the existing package and executable identity; the branding migration must be reviewed independently before release.

## Skill portability

Oh My Vibe-specific skills should be kept portable when possible. Use `.agents/skills/` for harness-agnostic skills. Use `.opencode/skills/`, `.codex/skills/`, `.pi/skills/`, `.claude/skills/`, or `.vibe/skills/` only for harness-specific variants. Hermes-global skills are copied into the repository only when they are directly specific to Oh My Vibe.
