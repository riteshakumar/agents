#!/usr/bin/env python3
"""
MCP client "agent" that connects to an MCP server and calls tools.
Run: python3 agent.py --demo
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from mcp import ClientSession, types
from mcp.client.streamable_http import streamable_http_client


def parse_json(s: str) -> dict[str, Any]:
    if not s:
        return {}
    return json.loads(s)


async def list_tools(session: ClientSession) -> None:
    tools = await session.list_tools()
    print("Available tools:")
    for tool in tools.tools:
        print(f"- {tool.name}")


async def demo(session: ClientSession) -> None:
    print("Running demo tool calls...")
    add_result = await session.call_tool("add", arguments={"a": 7, "b": 5})
    wc_result = await session.call_tool("word_count", arguments={"text": "hello from MCP"})
    time_result = await session.call_tool("current_time", arguments={})

    for label, result in (
        ("add", add_result),
        ("word_count", wc_result),
        ("current_time", time_result),
    ):
        content = result.content[0]
        if isinstance(content, types.TextContent):
            print(f"{label} -> {content.text}")
        else:
            print(f"{label} -> {content}")


async def call_tool(session: ClientSession, name: str, args: dict[str, Any]) -> None:
    result = await session.call_tool(name, arguments=args)
    content = result.content[0]
    if isinstance(content, types.TextContent):
        print(content.text)
    else:
        print(content)


async def run(args: argparse.Namespace) -> None:
    async with streamable_http_client(args.server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if args.list_tools:
                await list_tools(session)
                return

            if args.demo:
                await demo(session)
                return

            if args.tool:
                payload = parse_json(args.args)
                await call_tool(session, args.tool, payload)
                return

            await list_tools(session)


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP tool-calling agent")
    parser.add_argument(
        "--server-url",
        default="http://localhost:8000/mcp",
        help="MCP streamable HTTP endpoint",
    )
    parser.add_argument("--list-tools", action="store_true")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--tool", type=str, help="Tool name to call")
    parser.add_argument("--args", type=str, default="", help='JSON args, e.g. {"a":1,"b":2}')

    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
