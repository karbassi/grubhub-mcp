from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP

from src.grubhub_mcp import server

ENV_VARS = (
    "GRUBHUB_MCP_TRANSPORT",
    "GRUBHUB_MCP_HOST",
    "GRUBHUB_MCP_PORT",
    "GRUBHUB_MCP_ALLOWED_HOSTS",
    "GRUBHUB_MCP_ALLOWED_ORIGINS",
    "GRUBHUB_MCP_READ_ONLY",
    "FASTMCP_HOST",
    "FASTMCP_PORT",
)

MUTATING_TOOLS = {
    "login", "logout", "send_login_otp", "verify_login_otp", "create_account",
    "send_password_reset", "create_cart", "add_to_cart", "update_cart_item",
    "remove_from_cart", "apply_promo_code", "set_tip", "place_order", "reorder",
    "post_delivery_tip", "update_profile", "add_address", "add_favorite",
    "remove_favorite", "change_password", "apply_gift_card",
}


def tool_names(mcp: FastMCP) -> set[str]:
    return {tool.name for tool in asyncio.run(mcp.list_tools())}


class MainTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {})
        self.env.start()
        self.addCleanup(self.env.stop)
        for var in ENV_VARS:
            os.environ.pop(var, None)
        self.calls: list[tuple[FastMCP, dict]] = []

        def fake_run(instance, *args, **kwargs):
            self.calls.append((instance, kwargs))

        run_patch = patch.object(FastMCP, "run", fake_run)
        run_patch.start()
        self.addCleanup(run_patch.stop)

    def run_main(self, **env):
        os.environ.update(env)
        server.main()
        self.assertEqual(len(self.calls), 1)
        return self.calls[0]

    def test_defaults_to_stdio_with_all_tools(self):
        instance, kwargs = self.run_main()
        self.assertEqual(kwargs, {"transport": "stdio"})
        self.assertTrue(MUTATING_TOOLS <= tool_names(instance))

    def test_http_defaults_to_loopback_with_dns_rebinding_protection(self):
        instance, kwargs = self.run_main(GRUBHUB_MCP_TRANSPORT="http")
        self.assertEqual(kwargs, {"transport": "streamable-http"})
        self.assertEqual(instance.settings.host, "127.0.0.1")
        self.assertEqual(instance.settings.port, 8507)
        security = instance.settings.transport_security
        self.assertTrue(security.enable_dns_rebinding_protection)
        self.assertEqual(security.allowed_hosts, ["127.0.0.1:8507", "localhost:8507", "[::1]:8507"])
        self.assertEqual(security.allowed_origins, [])

    def test_http_host_and_port_from_env(self):
        for host in ("127.0.0.1", "localhost", "::1"):
            with self.subTest(host=host):
                self.calls.clear()
                instance, _ = self.run_main(
                    GRUBHUB_MCP_TRANSPORT="http", GRUBHUB_MCP_HOST=host, GRUBHUB_MCP_PORT="9000",
                )
                self.assertEqual(instance.settings.host, host)
                self.assertEqual(instance.settings.port, 9000)
                self.assertIn("localhost:9000", instance.settings.transport_security.allowed_hosts)

    def test_http_settings_override_fastmcp_env(self):
        instance, _ = self.run_main(
            GRUBHUB_MCP_TRANSPORT="http", FASTMCP_HOST="0.0.0.0", FASTMCP_PORT="1234",
        )
        self.assertEqual(instance.settings.host, "127.0.0.1")
        self.assertEqual(instance.settings.port, 8507)

    def test_http_extra_allowed_hosts_and_origins(self):
        instance, _ = self.run_main(
            GRUBHUB_MCP_TRANSPORT="http",
            GRUBHUB_MCP_ALLOWED_HOSTS="mcp.ali.fyi, other.example ,",
            GRUBHUB_MCP_ALLOWED_ORIGINS="https://mcp.ali.fyi",
        )
        security = instance.settings.transport_security
        self.assertEqual(security.allowed_hosts[-2:], ["mcp.ali.fyi", "other.example"])
        self.assertEqual(security.allowed_origins, ["https://mcp.ali.fyi"])

    def test_http_refuses_non_loopback_host(self):
        # No auth on the endpoint: anything that can reach it acts as the saved login.
        for host in ("0.0.0.0", "::", "100.72.126.89", "example.com"):
            with self.subTest(host=host):
                os.environ.update(GRUBHUB_MCP_TRANSPORT="http", GRUBHUB_MCP_HOST=host)
                with self.assertRaises(SystemExit):
                    server.main()
                self.assertEqual(self.calls, [])

    def test_http_refuses_bad_port(self):
        for port in ("abc", "0", "70000"):
            with self.subTest(port=port):
                os.environ.update(GRUBHUB_MCP_TRANSPORT="http", GRUBHUB_MCP_PORT=port)
                with self.assertRaises(SystemExit):
                    server.main()
                self.assertEqual(self.calls, [])

    def test_rejects_unknown_transport(self):
        os.environ["GRUBHUB_MCP_TRANSPORT"] = "sse"
        with self.assertRaises(SystemExit):
            server.main()
        self.assertEqual(self.calls, [])

    def test_read_only_env_drops_mutating_tools(self):
        for value in ("1", "true", "YES", "on"):
            with self.subTest(value=value):
                self.calls.clear()
                instance, _ = self.run_main(GRUBHUB_MCP_TRANSPORT="http", GRUBHUB_MCP_READ_ONLY=value)
                names = tool_names(instance)
                self.assertNotIn("place_order", names)
                self.assertEqual(names & MUTATING_TOOLS, set())
                self.assertEqual(names, set(server.READ_ONLY_TOOLS))

    def test_read_only_falsy_keeps_all_tools(self):
        for value in ("", "0", "false", "no"):
            with self.subTest(value=value):
                self.calls.clear()
                instance, _ = self.run_main(GRUBHUB_MCP_READ_ONLY=value)
                self.assertIn("place_order", tool_names(instance))


class ReadOnlyServerTests(unittest.TestCase):
    def test_full_server_is_exactly_reads_plus_mutations(self):
        # Fails when a tool is added without being classified as read or mutating.
        self.assertEqual(tool_names(server.create_server()), set(server.READ_ONLY_TOOLS) | MUTATING_TOOLS)

    def test_read_only_server_lists_only_reads(self):
        names = tool_names(server.create_server(read_only=True))
        self.assertEqual(names, set(server.READ_ONLY_TOOLS))
        for read in ("get_order_history", "get_order", "search_restaurants", "get_menu"):
            self.assertIn(read, names)

    def test_read_only_server_cannot_call_place_order(self):
        read_only = server.create_server(read_only=True)
        with self.assertRaises(Exception):
            asyncio.run(read_only.call_tool("place_order", {"cart_id": "x"}))


if __name__ == "__main__":
    unittest.main()
