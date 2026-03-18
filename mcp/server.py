#!/usr/bin/env python3
"""
Minimal MCP server exposing a few tools and a resource.
Run: python3 server.py
"""

from __future__ import annotations

import datetime as dt

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MCP Demo Server", json_response=True)


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@mcp.tool()
def word_count(text: str) -> int:
    """Count words in a string."""
    return len([w for w in text.split() if w.strip()])


@mcp.tool()
def current_time() -> str:
    """Get the current local time (ISO format)."""
    return dt.datetime.now().isoformat(timespec="seconds")


@mcp.resource("note://{title}")
def get_note(title: str) -> str:
    """Return a simple note template."""
    return f"Note: {title}\n- "


if __name__ == "__main__":
    # Streamable HTTP transport by default
    mcp.run(transport="streamable-http")
