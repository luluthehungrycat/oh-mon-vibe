## Context

Oh My Vibe has an internal Python entry-point registry, advisory command
analyzers, and host-owned Bash permissions. Those pieces do not yet define a
user-facing package format, disabled activation lifecycle, plugin permission
rules, or a plugin sandbox protocol. Hermes Agent's portable Agent Plugins v1
is a useful package-shape reference, but its documented format does not define
trust, permissions, provenance, or sandboxing. OpenCode's native modules are
also not a manifest or trust standard.

## Goals / Non-Goals

**Goals:**

- Define an OMV-owned JSON plugin package contract derived from portable Agent
  Plugins v1 without claiming Hermes or OpenCode compatibility.
- Keep installed plugins inert until explicit user enablement.
- Prefer Hermes-style lifecycle boundaries: discovery, validation, registration,
  activation, failure isolation, and shutdown cleanup.
- Make command analysis smart by default: deterministic destructive denial,
  automatic approval for clearly safe work, and user approval for ambiguity.
- Preserve granular user `always`, `ask`, and `deny` rules for plugin actions.
- Define optional and required plugin sandbox expectations with host-owned
  selection and fail-closed behavior.

**Non-Goals:**

- Native Hermes or OpenCode plugin compatibility.
- A plugin marketplace, remote installer, or dynamic untrusted installation.
- Running arbitrary plugin code in-process without manifest validation and
  explicit enablement.
- Treating thread timeouts or metadata as process isolation.
- Implementing a standalone SDK in this change.

## Decisions

### JSON manifest and fixed package layout

Use `plugin.json` rather than YAML. JSON matches the portable Agent Plugins v1
shape, has deterministic standard-library parsing, and avoids adding YAML parser
behavior to the trust boundary. A package contains a root `plugin.json`, an
OMV entry point, and optional fixed `skills/` and `mcp.json` components. The
manifest includes `schema`, `name`, semantic `version`, `kind`, `capabilities`,
`entrypoint`, `activation`, `trust`, `sandbox`, and lifecycle metadata. Unknown
fields are retained as metadata but never grant authority.

Discovery scans `$OMV_HOME/plugins/` and the project `.omv/plugins/` directory
without importing plugin code. The enabled-plugin configuration is an explicit
allowlist. Project plugins cannot silently shadow a global plugin with the same
name; duplicate identities are diagnosed and skipped.

### Hermes-style lifecycle

The lifecycle is `discover -> parse -> validate -> enable -> register ->
activate -> invoke -> deactivate`. Discovery and validation are cheap and
manifest-only. Registration and activation happen only for enabled plugins.
Each plugin has a bounded lifecycle context, and registration/activation
failures are isolated. Shutdown invokes cleanup for activated plugins and
records failures without blocking other cleanup or host shutdown.

### Host-owned smart command policy

Plugin analyzers return typed advisory classifications: `allow`, `ask`, or
`deny`, plus a reason and optional sandbox eligibility. The host applies this
precedence:

1. deterministic dangerous-command denial;
2. explicit user `deny` rule;
3. required path/permission checks and sandbox requirements;
4. plugin advisory `deny` or `ask`;
5. explicit user `always` rule when no core safeguard is violated;
6. advisory `allow` for clearly safe work;
7. human approval for remaining ambiguity.

A deterministic denial cannot be overridden by a plugin or an `always` rule.
Users may define granular plugin/action/command rules with `always`, `ask`, or
`deny`; the default is `ask` for side-effecting plugin actions. The policy
reuses the existing typed permission model rather than adding a surface-local
approval path.

### Plugin sandbox expectations

The manifest declares `sandbox: optional | required`; omission means
`optional`. The user config declares `plugins.sandbox: off | auto | required`.

- `off` runs only plugins that do not require isolation; a required plugin is
  refused before activation.
- `auto` sandboxes optional and required plugins when a compatible backend and
  process adapter exist; an unavailable backend makes optional plugins ask or
  refuse according to the user fallback, and always refuses required plugins.
- `required` refuses plugins that cannot provide an isolatable process contract.

In-process plugins are trusted code and cannot claim sandboxed execution. A
sandboxed plugin must expose a versioned stdio protocol and run in a separate
process through a backend that reports availability, network isolation,
writable-workdir scope, timeout, and cleanup. No plugin backend is selected by
plugin code; the host owns the decision and argv construction.

### Trust, failure, and diagnostics

Manifest trust is explicit: `trusted_in_process` or `isolated_process`. The
host accepts the former only for the initial implementation. It rejects the
latter until the process protocol, resource limits, cancellation, cleanup, and
capability evidence are implemented. Diagnostics identify plugin, lifecycle
phase, decision, trust, isolation, timeout, and failure reason.

### Migration

Existing `omv.plugins` Python entry points remain an internal compatibility
path while packages migrate. Public package activation requires `plugin.json`
validation and explicit enablement. The registry must not execute a package
entry point merely because it is installed.

## Risks / Trade-offs

- **JSON is less comment-friendly than YAML** → deterministic parsing and no
  new parser in the trust boundary are more important.
- **Smart analysis can be wrong** → deterministic denials and user rules remain
  authoritative; ambiguity becomes approval.
- **Optional sandboxing adds startup cost** → users control the default policy;
  required plugins never silently fall back.
- **Separate plugin processes require a protocol** → this is deliberately
  specified before implementation rather than faking isolation.
- **Portable Agent Plugins v1 remains incomplete for OMV safety** → reuse its
  package shape only; do not claim format compatibility.
