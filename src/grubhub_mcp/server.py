"""Grubhub MCP Server — search restaurants, browse menus, manage cart, place orders."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .tools import auth, search, restaurant, cart, order, account, payments

INSTRUCTIONS = (
    "Grubhub MCP server. Use these tools to search for restaurants, "
    "browse menus, manage a shopping cart, place food delivery/pickup "
    "orders, and manage your Grubhub account. "
    "Start by searching for restaurants near a location. "
    "Login is required for placing orders, viewing order history, "
    "and account management. Search and menu browsing work without login."
)

READ_ONLY_INSTRUCTIONS = (
    "Grubhub MCP server (read-only). Use these tools to search for "
    "restaurants, browse menus, and view carts, orders, order history, "
    "addresses, favorites and payment methods. Nothing can be ordered, "
    "changed or logged in/out from this server. Order history and account "
    "views need a login saved by a separate, non-read-only instance."
)

# Tools that never change Grubhub or local session state. Read-only mode keeps
# only these, so any tool added later is excluded until it is classified here.
READ_ONLY_TOOLS = frozenset({
    "get_session_info",
    "search_restaurants",
    "autocomplete_search",
    "get_restaurant",
    "get_menu",
    "get_menu_item",
    "get_cart",
    "get_order",
    "get_order_history",
    "track_order",
    "get_profile",
    "get_addresses",
    "get_favorites",
    "get_payment_methods",
    "get_gift_card_balance",
})

LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
DEFAULT_PORT = 8507
_TRUTHY = {"1", "true", "yes", "on"}


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY


def _env_list(name: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


class _ReadOnlyRegistrar:
    """Stands in for FastMCP during registration, dropping mutating tools."""

    def __init__(self, server: FastMCP) -> None:
        self._server = server

    def tool(self, name: str | None = None, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        register = self._server.tool(name=name, **kwargs)

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            if (name or fn.__name__) in READ_ONLY_TOOLS:
                return register(fn)
            return fn

        return decorator

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._server, attr)


def create_server(*, read_only: bool = False) -> FastMCP:
    """Build the server; ``read_only`` registers only non-mutating tools."""
    server = FastMCP(
        "grubhub",
        instructions=READ_ONLY_INSTRUCTIONS if read_only else INSTRUCTIONS,
    )
    registrar = _ReadOnlyRegistrar(server) if read_only else server
    for module in (auth, search, restaurant, cart, order, account, payments):
        module.register(registrar)
    return server


mcp = create_server()


def _configure_http(server: FastMCP) -> None:
    host = os.environ.get("GRUBHUB_MCP_HOST", "127.0.0.1").strip()
    if host not in LOOPBACK_HOSTS:
        # No auth on the endpoint: anything that can reach it acts as the saved login.
        raise SystemExit(
            f"GRUBHUB_MCP_HOST must be one of {', '.join(LOOPBACK_HOSTS)} (got {host!r}); "
            "the HTTP endpoint has no authentication."
        )
    raw_port = os.environ.get("GRUBHUB_MCP_PORT", str(DEFAULT_PORT)).strip()
    try:
        port = int(raw_port)
    except ValueError:
        raise SystemExit(f"GRUBHUB_MCP_PORT must be an integer (got {raw_port!r})") from None
    if not 0 < port < 65536:
        raise SystemExit(f"GRUBHUB_MCP_PORT must be between 1 and 65535 (got {port})")

    server.settings.host = host
    server.settings.port = port
    server.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            f"127.0.0.1:{port}",
            f"localhost:{port}",
            f"[::1]:{port}",
            *_env_list("GRUBHUB_MCP_ALLOWED_HOSTS"),
        ],
        allowed_origins=_env_list("GRUBHUB_MCP_ALLOWED_ORIGINS"),
    )


def main() -> None:
    transport = os.environ.get("GRUBHUB_MCP_TRANSPORT", "stdio").strip().lower() or "stdio"
    if transport not in ("stdio", "http"):
        raise SystemExit(f"GRUBHUB_MCP_TRANSPORT must be 'stdio' or 'http' (got {transport!r})")

    server = create_server(read_only=True) if _env_flag("GRUBHUB_MCP_READ_ONLY") else mcp
    if transport == "stdio":
        server.run(transport="stdio")
        return
    _configure_http(server)
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
