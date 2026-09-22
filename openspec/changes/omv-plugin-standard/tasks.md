## 1. Manifest and package discovery

- [x] 1.1 Add typed `plugin.json` manifest models with schema/version, identity, kind, capability, entrypoint, activation, trust, and sandbox fields.
- [x] 1.2 Implement manifest-only discovery under `$OMV_HOME/plugins/` and project `.omv/plugins/` without importing disabled plugin code.
- [x] 1.3 Implement explicit enablement, duplicate identity diagnostics, fixed component layout validation, and safe path containment.
- [x] 1.4 Preserve the existing entry-point registry as an internal migration path while requiring validated manifests for public package activation.

## 2. Hermes-style lifecycle

- [x] 2.1 Add typed lifecycle phases for discover, validate, enable, register, activate, invoke, deactivate, and cleanup.
- [x] 2.2 Add bounded lifecycle contexts and per-plugin failure isolation for registration and activation.
- [x] 2.3 Add shutdown cleanup ordering, timeout handling, and structured lifecycle diagnostics.
- [x] 2.4 Project plugin lifecycle state through existing host-owned diagnostics without exposing registries to clients.

## 3. Host-owned permission policy

- [x] 3.1 Add typed plugin analyzer results for `allow`, `ask`, and `deny` with reasons and sandbox eligibility.
- [x] 3.2 Reuse deterministic Bash guardrails for dangerous-command denial and preserve host precedence over plugin output.
- [x] 3.3 Add granular per-plugin, capability, action, and command `always`/`ask`/`deny` rules with `ask` defaults for side effects.
- [x] 3.4 Add ambiguity handling that requests human approval rather than automatic approval.
- [x] 3.5 Add regression coverage for safe auto-allow, ambiguity, destructive denial, explicit rules, and precedence conflicts.

## 4. Plugin sandbox contract
- [x] 4.1 Add user plugin sandbox policy `off`/`auto`/`required` and manifest expectation `optional`/`required`.
- [x] 4.2 Define the versioned isolated-process stdio protocol and typed capability evidence.
- [x] 4.3 Integrate only host-selected Bubblewrap/Firejail backends; plugin code cannot select or construct sandbox argv.
- [x] 4.4 Refuse required isolation when the backend, protocol, network, workdir, timeout, or cleanup evidence is unavailable.
- [x] 4.5 Add regression coverage for optional opt-in, required refusal, startup failure, capability evidence, and no unsandboxed fallback.

## 5. Package components and migration
- [x] 5.1 Load fixed `skills/` and `mcp.json` components with package-root containment and per-component failure isolation.
- [x] 5.2 Define migration diagnostics for existing Python entry-point plugins without silently enabling them as packages.
- [x] 5.3 Update user documentation with the manifest schema, install-disabled workflow, lifecycle, permission rules, and sandbox policy.
- [x] 5.4 Update the built-in Vibe skill and relevant config schema documentation if new plugin settings become user-configurable.

## 6. Conformance and release gate
- [x] 6.1 Add fixtures for every manifest, lifecycle, permission, and sandbox requirement.
- [x] 6.2 Add a host conformance runner that records structured evidence and refuses incomplete plugin claims.
- [x] 6.3 Verify vanilla Vibe defaults remain unchanged when no OMV plugin configuration is present.
- [x] 6.4 Run focused tests, formatting, type checks, CLI smoke checks, and OpenSpec validation before implementation completion.
- [x] 6.5 Defer standalone SDK extraction and cross-harness compatibility claims until the OMV contract passes review.
