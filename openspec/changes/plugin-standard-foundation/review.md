# Adapter and isolation contract review

## Review scope

Reviewed `adapter-mappings.md`, the plugin foundation design, the current plugin
registry, the safety policy, and the sandbox capability contract against issue
#4 and the plugin conformance requirements.

## Findings

| Check | Result | Evidence |
| --- | --- | --- |
| Versioned manifest | Pass | API version `1` is required before registration; unknown versions are rejected. |
| Capability vocabulary | Pass | `analyzer` and `sandbox_backend` are the only declared capabilities; kind boundaries are validated. |
| Host authority | Pass | Analyzer results remain advisory; deterministic deny, human denial, and sandbox policy remain host-owned. |
| Trust boundary | Pass | Only `trusted_in_process` is accepted; `process_isolated` is refused without a supervisor and cleanup contract. |
| Failure and diagnostics | Pass | Manifest rejection and registration failure have distinct structured diagnostic events. |
| Sandbox evidence | Pass | Existing sandbox capabilities expose availability, network isolation, and writable-workdir state; plugin backend registration remains unconsumed metadata. |
| Adapter mapping completeness | Partial | Hermes Agent and OpenCode concepts are mapped for all required contract fields. Transport-specific API names and wire fixtures remain unresolved. |
| SDK readiness | Blocked | At least one harness owner must review the transport mapping and isolation design before SDK implementation. |

## Decision

The host-side contract is internally consistent and the OpenSpec change passes
strict validation. The project MUST NOT claim Hermes Agent or OpenCode
compatibility, process isolation, or SDK readiness based on this review. Task
4.3 remains open until a harness-specific mapping and isolation design receive
owner review.

## Required follow-up

1. Obtain review from a Hermes Agent or OpenCode integration owner.
2. Resolve transport-specific manifest, permission, diagnostic, and lifecycle
   wire fields.
3. Add adapter fixtures for the reviewed mapping.
4. Re-run the SDK readiness checklist before opening a standalone SDK proposal.
