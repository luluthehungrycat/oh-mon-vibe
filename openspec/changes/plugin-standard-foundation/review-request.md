# Adapter owner review request

## Scope

Please review `adapter-mappings.md` against the current Hermes Agent and OpenCode
extension contracts. This is a design review only; it does not request code
changes, SDK publication, or compatibility claims.

## Reviewers requested

- One Hermes Agent plugin or portable Agent Plugins maintainer.
- One OpenCode plugin or extension maintainer.
- One Oh My Vibe safety/permissions reviewer.

A single reviewer MAY cover multiple roles when they have direct ownership of
the relevant host contract, but the review record MUST identify which roles
were covered.

## Questions requiring an explicit answer

1. **Manifest:** Where should the Oh My Vibe name, semantic version, API version,
   kind, and capabilities be represented in the host's native extension format?
2. **Enablement:** Can an installed-but-disabled extension be guaranteed not to
   import or execute? Identify the exact lifecycle point and fixture.
3. **Authority:** Where are advisory decisions, required permissions, and
   explicit human denial represented? Confirm that an adapter cannot promote an
   advisory allow into host authority.
4. **Sandbox evidence:** Which native fields carry backend availability, network
   isolation, writable-workdir scope, and fallback state? Identify any field the
   host cannot represent.
5. **Diagnostics:** How are manifest rejection, registration failure, timeout,
   malformed output, unavailable sandbox, and isolation refusal surfaced?
6. **Isolation:** Does the host provide a process supervisor, resource limits,
   cancellation, and cleanup guarantee? If not, confirm that untrusted plugins
   are refused rather than labeled isolated.
7. **Versioning:** Does the host support exact API negotiation or only native
   additive evolution? Confirm that unknown versions and capabilities are not
   silently downgraded.
8. **Lifecycle:** What are the discovery, registration, invocation, failure,
   shutdown, and cleanup boundaries? Identify the conformance fixture for each.

## Required review output

The reviewer MUST return:

- answers to all eight questions;
- reviewed, unresolved, or rejected status for every mapping row;
- one valid and one invalid fixture outline per declared capability;
- explicit confirmation of whether compatibility can be claimed;
- named follow-up owners for unresolved wire details.

Until this packet is answered, task 4.3 remains open and the project MUST NOT
open a standalone SDK implementation proposal or claim cross-harness
compatibility.
