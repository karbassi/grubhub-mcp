# Grubhub MCP Server

An MCP (Model Context Protocol) server that provides programmatic access to Grubhub's food delivery platform. Search restaurants, browse menus, manage your cart, place orders, and track deliveries — all through MCP tools.

## Features

- **Search & Discovery** — Find restaurants by location, cuisine, or keyword with autocomplete
- **Restaurant & Menus** — View restaurant details, full menus, item options and pricing
- **Cart Management** — Create carts, add/remove items, apply promo codes, set tips
- **Order Flow** — Place orders, track deliveries in real-time, reorder past meals
- **Account Management** — Manage profile, saved addresses, favorites, and passwords
- **Payments** — View saved payment methods, check gift card balances

### All 36 Tools

| Category | Tools |
|----------|-------|
| **Auth** | `login`, `logout`, `get_session_info`, `send_login_otp`, `verify_login_otp`, `create_account`, `send_password_reset` |
| **Search** | `search_restaurants`, `autocomplete_search` |
| **Restaurant** | `get_restaurant`, `get_menu`, `get_menu_item` |
| **Cart** | `create_cart`, `get_cart`, `add_to_cart`, `update_cart_item`, `remove_from_cart`, `apply_promo_code`, `set_tip` |
| **Order** | `place_order`, `get_order`, `get_order_history`, `track_order`, `reorder`, `post_delivery_tip` |
| **Account** | `get_profile`, `update_profile`, `get_addresses`, `add_address`, `get_favorites`, `add_favorite`, `remove_favorite`, `change_password` |
| **Payments** | `get_payment_methods`, `get_gift_card_balance`, `apply_gift_card` |

## Installation

### Claude Code Plugin (Recommended)

```bash
claude plugin marketplace add aserper/grubhub-mcp
claude plugin install grubhub-mcp@grubhub-marketplace
```

### uvx (No Installation Required)

Add to your Claude Code MCP settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "grubhub": {
      "command": "uvx",
      "args": ["--from", "grubhub-mcp", "grubhub"]
    }
  }
}
```

### Manual / From Source

Requires Python 3.11+.

```bash
git clone https://github.com/aserper/grubhub-mcp.git
cd grubhub-mcp
uv venv && source .venv/bin/activate
uv pip install -e .
```

Then add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "grubhub": {
      "command": "/path/to/grubhub-mcp/.venv/bin/grubhub"
    }
  }
}
```

## Usage with Other MCP Clients

Run the server over stdio:

```bash
# With uvx (no install needed)
uvx --from grubhub-mcp grubhub

# Or from a local install
grubhub

# Or as a Python module
python -m grubhub_mcp
```

## Shared HTTP server

By default every client starts its own stdio process. To run one long-lived server that many clients share, use the streamable-HTTP transport:

```bash
GRUBHUB_MCP_TRANSPORT=http GRUBHUB_MCP_READ_ONLY=1 GRUBHUB_MCP_PORT=8507 grubhub
```

```json
{
  "mcpServers": {
    "grubhub": { "type": "http", "url": "http://127.0.0.1:8507/mcp" }
  }
}
```

| Variable | Default | Description |
|---|---|---|
| `GRUBHUB_MCP_TRANSPORT` | `stdio` | `stdio` or `http` (streamable HTTP, served at `/mcp`) |
| `GRUBHUB_MCP_HOST` | `127.0.0.1` | Bind address. Must be `127.0.0.1`, `localhost`, or `::1`; anything else exits |
| `GRUBHUB_MCP_PORT` | `8507` | Listen port |
| `GRUBHUB_MCP_ALLOWED_HOSTS` | (none) | Comma-separated extra `Host` header values to accept, e.g. a reverse proxy's `mcp.example.com` |
| `GRUBHUB_MCP_ALLOWED_ORIGINS` | (none) | Comma-separated `Origin` values to accept from browser-based clients, e.g. `https://mcp.example.com` |
| `GRUBHUB_MCP_READ_ONLY` | off | When `1`/`true`/`yes`/`on`, register only non-mutating tools (any transport) |

These settings take precedence over FastMCP's own `FASTMCP_HOST` / `FASTMCP_PORT` environment variables.

The endpoint has **no authentication**: anything that can connect to it can use every registered tool with your saved Grubhub login, including **placing real food orders charged to your saved payment method**, changing your address and password, and logging you out. So:

- **Set `GRUBHUB_MCP_READ_ONLY=1` for any shared HTTP deployment.** It is off by default only so existing stdio setups keep every tool. Read-only mode exposes just the tools that change nothing: `get_session_info`, `search_restaurants`, `autocomplete_search`, `get_restaurant`, `get_menu`, `get_menu_item`, `get_cart`, `get_order`, `get_order_history`, `track_order`, `get_profile`, `get_addresses`, `get_favorites`, `get_payment_methods`, `get_gift_card_balance`. Ordering, cart, tip, gift-card, profile, address, favorite, password and login/logout/OTP tools are not registered at all, so a client cannot call them even if its own permissions would allow it.
- Read-only mode also leaves out the login tools, because a login, logout or OTP verification replaces the session every client shares. Log in from a separate stdio instance that uses the same `GRUBHUB_SESSION_DIR`, then restart the HTTP server so it loads the new session. Token refreshes are shared through the session file automatically.
- The server only binds to loopback. Any local process can still connect, so only use HTTP mode on a machine where every local user and process is trusted with your Grubhub account.
- DNS-rebinding protection is always on: requests whose `Host` is not `127.0.0.1:<port>`, `localhost:<port>`, `[::1]:<port>` or an entry in `GRUBHUB_MCP_ALLOWED_HOSTS` are rejected, as are requests carrying an `Origin` not listed in `GRUBHUB_MCP_ALLOWED_ORIGINS`. That check **only** stops web pages from reaching the server through DNS rebinding. It does not authenticate anyone.
- To reach it from another machine, put it behind a reverse proxy that **controls who can connect** (a bearer token, mTLS, an IP allowlist on a private network, or similar), and add the proxy's hostname to `GRUBHUB_MCP_ALLOWED_HOSTS`. Never expose the port or the proxy publicly without access control.

## Authentication

**No login required** for browsing — search restaurants, view menus, and check prices without an account. The server automatically creates an anonymous session.

**Login required** for ordering, account management, and order history:

```
Use the login tool with my email and password
```

Supports email/password login and OTP (one-time passcode) authentication.

Sessions are stored in `~/.grubhub-mcp/session.json` (override the directory with
`GRUBHUB_SESSION_DIR`). Access tokens are refreshed on use, including before
expiry when Grubhub supplies expiry metadata and once after an authenticated
request returns 401. Rotated tokens are saved for the next server invocation.
Refresh responses that omit account metadata do not erase your login identity.
Concurrent refreshes are serialized within the client, and on POSIX systems
across server processes sharing the session directory. Session writes are atomic
and use private file permissions. Grubhub's lifetime fields are in minutes;
the observed access/refresh lifetimes are one hour / 30 days, but server policy
may change.
There is no background keep-alive: a revoked or expired refresh token still
requires a new login. Do not share your session file; it contains credentials.

## Order History Pagination

`get_order_history` uses server-side pagination so older orders are reachable.
`page_num` is **1-based** (default `1`), and `page_size` defaults to `20`.
Iterate from `1` through `pagination.total_pages` to retrieve the full history.
Both values must be positive. Order-detail and reorder fallbacks search across
all available history pages.

**Migration from v1.1.6:** callers using the old 0-based `page_num` must add one
to their page index. The response now provides `total_pages` and `current_page`
instead of the legacy `total_orders` value, which only counted a capped subset.

## How It Works

The API endpoints were reverse-engineered from the Grubhub Android app (v2026.11.1) by decompiling the APK with jadx and analyzing the Retrofit service interfaces, OkHttp interceptors, and data models.

Key technical details:
- **Base API**: `https://api-gtm.grubhub.com`
- **Auth**: Bearer token via email/password or anonymous sessions
- **Transport**: REST/JSON for most endpoints, Protobuf for some BFF services
- **Headers**: Mimics the Android app's request headers including `x-gh-browser-id`

## Project Structure

```
src/grubhub_mcp/
├── __init__.py
├── __main__.py        # python -m entry point
├── server.py          # MCP server setup and tool registration
├── client.py          # HTTP client with auth and header management
├── auth.py            # Authentication flows (login, anonymous, OTP, refresh)
└── tools/
    ├── auth.py        # Auth tools (login, logout, OTP, account creation)
    ├── search.py      # Restaurant search and autocomplete
    ├── restaurant.py  # Restaurant details, menus, menu items
    ├── cart.py        # Cart CRUD, promo codes, tips
    ├── order.py       # Place orders, track, reorder, order history
    ├── account.py     # Profile, addresses, favorites, password
    └── payments.py    # Payment methods, gift cards
```

## Development

Run the regression suite with:

```
uv run python -m unittest discover -s tests -v
```

CI runs tests on pushes and pull requests, and the release job runs them before
publishing. The package currently requires MCP 1.x (`mcp<2`).

## Disclaimer

This project is for educational and personal use. It is not affiliated with or endorsed by Grubhub. Use responsibly and in accordance with Grubhub's terms of service.

## License

MIT
