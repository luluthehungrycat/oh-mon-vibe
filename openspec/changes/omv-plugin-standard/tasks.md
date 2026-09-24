## 1. Upstream reconciliation

- [x] 1.1 Merge upstream Mistral Vibe v2.25.7 into downstream main with a preserved merge commit.
- [x] 1.2 Integrate the PR branch on top of the reconciliation merge without rewriting PR history.
- [x] 1.3 Keep upstream Agent Plugins resolver modules as the only package resolver.

## 2. Canonical Agent Plugins boundary

- [x] 2.1 Use root Agent Plugins 1.0 `plugin.json`, standard `mcp.json`, and fixed `skills/` through upstream code.
- [x] 2.2 Remove the custom `omv.plugin.v1` manifest, activation lifecycle, plugin permission config, and plugin sandbox API.
- [x] 2.3 Reserve `extensions["com.ohmyvibe"]` for inert future OMV metadata.
- [x] 2.4 Preserve the existing internal Python analyzer registry as separate from Agent Plugins packages.
- [x] 2.5 Add regression coverage for canonical package files and inert OMV extension metadata.

## 3. Scope and documentation

- [x] 3.1 Limit OMV package claims to standard skills/MCP and upstream discovery/inspection.
- [x] 3.2 Explicitly defer OMV-native analyzers, tools, hooks, and plugin-specific sandbox enforcement.
- [x] 3.3 Align README, built-in skill, safety documentation, changelog, and OpenSpec artifacts.

## 4. Verification

- [x] 4.1 Run focused resolver and MCP behavior tests.
- [ ] 4.2 Run Ruff, Pyright, OpenSpec validation, pre-commit, and build checks.
- [ ] 4.3 Run CI on the final draft PR head and preserve draft state.
