# CHANGELOG

<!-- version list -->

## v1.1.7 (2026-10-09)

### Bug Fixes

- Pin the MCP dependency to the compatible 1.x API and refresh/persist sessions safely.
- Paginate the full order history server-side and search all pages for order fallbacks.


## v1.1.6 (2026-05-06)

### Bug Fixes

- Reconstruct reorder carts from order history
  ([`7c40515`](https://github.com/aserper/grubhub-mcp/commit/7c40515eab25f0fc057d472ab3815892526c37ca))


## v1.1.5 (2026-05-06)

### Bug Fixes

- Harden cart creation and auth error handling
  ([`876d946`](https://github.com/aserper/grubhub-mcp/commit/876d9466000c47257a30573cb8ff1faa799a0a52))


## v1.1.4 (2026-05-06)

### Bug Fixes

- Harden auth guards and order history fallbacks
  ([`4a8ca08`](https://github.com/aserper/grubhub-mcp/commit/4a8ca08303faac31708f7135318a513a3c3859e4))


## v1.1.3 (2026-03-24)

### Bug Fixes

- Fix search, autocomplete, profile, and payment endpoints
  ([`3f78fb2`](https://github.com/aserper/grubhub-mcp/commit/3f78fb2e7e4af6bcf6b41dd8b4dd7569badae63d))


## v1.1.2 (2026-03-24)

### Bug Fixes

- Correct API endpoint paths and diner_udid extraction
  ([`d523540`](https://github.com/aserper/grubhub-mcp/commit/d523540c00a0067bd9e34e7c43f6c65342f76c45))


## v1.1.1 (2026-03-24)

### Bug Fixes

- Add csrf_token to OTP verify flow and persist it across sessions
  ([`eb6f718`](https://github.com/aserper/grubhub-mcp/commit/eb6f718410261a23e2b79caa586b9656a73c6ab3))


## v1.1.0 (2026-03-24)

### Features

- Persist session to disk for stdio transports
  ([`44e14d1`](https://github.com/aserper/grubhub-mcp/commit/44e14d135a868b445d43da88961451f35a8dba58))


## v1.0.1 (2026-03-24)

### Bug Fixes

- Add build_command to semantic-release config
  ([`8843307`](https://github.com/aserper/grubhub-mcp/commit/88433073fd291c712c461d4e18e0960994892687))


## v1.0.0 (2026-03-24)

- Initial Release
