# Adapter mappings

This document is a design artifact for issue #4. It does not implement or claim
Hermes Agent or OpenCode interoperability. Each mapping is conceptual until the
host and harness owners review the transport-specific details.

## External contract observations

These observations are grounded in the current public documentation and are
inputs to, not proof of, adapter compatibility:

- [Hermes plugin guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins)
  describes native `plugin.yaml` plus `register(ctx)` plugins and a separate
  portable Agent Plugins v1 package format. The portable format uses
  `plugin.json`, skills, and MCP declarations; it explicitly does not define
  trust, permissions, provenance, or sandboxing. Native Hermes plugins do not
  expose a global `PLUGIN_API_VERSION`.
- [OpenCode plugin documentation](https://opencode.ai/docs/plugins/) describes
  JavaScript/TypeScript modules loaded from local plugin directories or npm
  packages. Its documented surface is hook- and event-based; it does not
  define the Oh My Vibe manifest, capability, or trust vocabulary.

Therefore the adapter mappings below are translations into each host's native
extension surface, not claims that either host natively implements the Oh My
Vibe contract. A real adapter MUST add the missing manifest, authority,
diagnostic, and isolation checks at its boundary.

## Shared authority contract

Both adapters MUST preserve these host-owned invariants:

- manifest API version and capability validation happen before registration;
- plugin results are advisory and cannot remove permissions, override explicit
  denial, or disable sandbox fallback safeguards;

- only trusted in-process plugins may run in the current host;
- untrusted or process-isolated plugins are refused until an isolating runtime
  and lifecycle contract exist;
- timeout, malformed output, callback failure, and unavailable sandbox state
  produce structured diagnostics and never automatic approval;
- sandbox backend registration is descriptive until a reviewed execution adapter
  consumes capability evidence.

The concrete host-side matrix is maintained in
`conformance-fixtures.md`; adapters must map those fixture IDs to native
installation, invocation, diagnostic, or refusal tests.

## Contract mapping

| Contract concept | Hermes Agent adapter | OpenCode adapter | Host invariant |
| --- | --- | --- | --- |
| Manifest | Map `name`, semantic `version`, API version, kind, and capabilities to the harness extension descriptor. | Map the same fields to the OpenCode plugin/extension metadata. | Reject unsupported API versions, unknown capabilities, and kind/capability mismatches before executable registration. |
| Discovery and enablement | Map the host enabled-plugin allowlist to the harness's explicit extension selection. | Map the allowlist to the OpenCode extension activation configuration. | Installed-but-disabled plugins are not imported or executed. |
| Decision | Map `allow`, `deny`, and `ask` to advisory analyzer output. | Map the same values to advisory analyzer output. | The host composes the result with deterministic policy; adapters never grant authority. |
| Permissions | Map required command, path, and approval scopes to the harness approval request metadata. | Map the same scopes to OpenCode permission prompts or refusal responses. | The host owns permission resolution and explicit human denial. |
| Sandbox state | Map backend, availability, network isolation, writable-workdir, and fallback state to harness-visible execution metadata. | Map the same capability evidence to OpenCode execution metadata. | Missing or contradictory evidence blocks sandbox claims and cannot trigger plugin backend execution. |
| Errors and diagnostics | Map manifest rejection, registration failure, timeout, malformed output, and isolation refusal to harness diagnostics. | Map the same failure classes to OpenCode diagnostics. | Diagnostics retain plugin identity, reason, trust level, and isolation status. |
| Timeout | Map the bounded analyzer timeout and terminal `ask` result. | Map the bounded analyzer timeout and terminal `ask` result. | Thread timeout is not process isolation; a timed-out plugin remains trusted-only. |
| Lifecycle | Map discovery, registration, invocation, failure isolation, and shutdown callbacks. | Map the same lifecycle states to the OpenCode extension lifecycle. | A plugin failure cannot prevent built-ins or other plugins from loading. |

## Conformance evidence required from an adapter

An adapter review MUST include fixtures showing:

1. a valid manifest is discovered and explicitly enabled;
2. disabled plugins are not imported;
3. unsupported versions, capabilities, and trust levels are rejected;
4. advisory allow cannot bypass deterministic deny, required approval, or
   sandbox selection;
5. timeout, exception, malformed output, and unavailable sandbox cases fail
   closed with structured diagnostics;
6. sandbox evidence includes backend availability, network isolation,
   writable-workdir behavior, and fallback state;
7. lifecycle failure isolation leaves built-ins and unrelated plugins usable;
8. all wire/API-specific mappings are identified as reviewed or unresolved.

The current repository satisfies host-side evidence for the registry and safety
analyzer. It does not yet satisfy adapter-specific evidence, so neither adapter
is standard-compatible or SDK-ready.

## Isolation and version negotiation

The current host supports only `trusted_in_process` plugins. A request for
`process_isolated` trust is rejected because no process supervisor, transport,
resource limit, cancellation protocol, or cleanup guarantee exists.

An adapter MUST reject an API version it does not understand. It MUST NOT
silently downgrade a manifest or reinterpret an unknown capability. A future
negotiation mechanism may be added only with an explicit version range and
compatibility result; until then, the exact supported API version is required.

## SDK extraction gate

A standalone SDK proposal remains blocked until all of the following are
reviewed and evidenced:

- stable manifest fields, capability vocabulary, and version policy;
- host-authoritative decision and permission semantics;
- trusted in-process and process-isolated boundaries, including refusal rules;
- timeout, failure, diagnostics, lifecycle, and cleanup behavior;
- conformance fixtures for every declared capability;
- at least one reviewed harness adapter mapping, with Hermes Agent and OpenCode
  mappings documented here before implementation claims;
- no unresolved contradiction between adapter mappings and host safety behavior.

Passing this checklist permits a separate SDK implementation proposal. It does
not authorize dynamic untrusted plugin installation or claim cross-harness
compatibility by itself.
