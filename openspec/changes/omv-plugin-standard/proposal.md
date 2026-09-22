## Why

Oh My Vibe currently has an internal Python entry-point registry, but it does not
provide a user-facing plugin package, disabled-install lifecycle, granular
plugin permission policy, or a defined plugin sandbox decision. Hermes Agent's
portable Agent Plugins v1 provides a useful package shape, while its native
plugin contract does not provide the trust and safety semantics Oh My Vibe
needs. Define an OMV-owned `plugin.json` standard now instead of forcing
compatibility with a host contract that cannot express these guarantees.

## What Changes

- Add an OMV-owned `plugin.json` manifest based on the portable Agent Plugins v1
  package shape, with explicit schema version, identity, capabilities, entry
  point, trust, lifecycle, permission, and sandbox expectations.
- Discover installed plugins without importing or executing them until the user
  explicitly enables them.
- Use a Hermes-inspired lifecycle: validate metadata, discover fixed package
  components, register callbacks, activate enabled plugins, isolate failures,
  and clean up on shutdown.
- Add host-owned smart command policy for plugin analyzers:
  - deterministic dangerous-command denial remains authoritative;
  - clearly safe commands can be auto-allowed;
  - ambiguity requests user approval;
  - users can override the policy with granular `always`, `ask`, and `deny`
    rules, matching vanilla Vibe/OpenCode expectations.
- Define an OMV plugin sandbox decision with three plugin-declared expectations:
  `never`, `optional`, and `required`, plus user policy controlling whether
  optional plugins run sandboxed.
- Refuse a plugin when its required sandbox or trust contract cannot be met;
  never reinterpret `required` as unsandboxed execution.
- Preserve host authority over permissions, denial, sandbox selection, result
  validation, diagnostics, and lifecycle cleanup.
- Add conformance fixtures for package validation, disabled activation,
  permission precedence, dangerous-command denial, ambiguity approval,
  sandbox decisions, failures, timeouts, and shutdown.
- Keep Hermes Agent and OpenCode adapters as optional future mappings; do not
  claim compatibility or extract an SDK from this change.

## Capabilities

### New Capabilities

- `omv-plugin-packages`: Defines the `plugin.json` manifest, package discovery,
  explicit enablement, fixed component layout, and Hermes-inspired lifecycle.
- `omv-plugin-permissions`: Defines host-authoritative smart command analysis,
  dangerous-command denial, ambiguity approval, and granular always/ask/deny
  overrides.
- `omv-plugin-sandboxing`: Defines plugin trust, optional/required sandbox
  expectations, user policy, capability evidence, and fail-closed refusal.

### Modified Capabilities

- None.

## Impact

This is an OMV-owned plugin contract and safety policy, not a compatibility
layer for native Hermes or OpenCode plugins. It affects plugin discovery,
configuration, command policy, sandbox selection, diagnostics, and lifecycle
management. Existing internal entry-point plugins require migration into the
new manifest contract before they can use the public package lifecycle.
