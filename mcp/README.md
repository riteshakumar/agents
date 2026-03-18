# MCP Agent (Python)

A minimal example of a tool-connected agent using the Model Context Protocol (MCP). It includes:

- `server.py`: MCP server exposing tools and a resource
- `agent.py`: MCP client that lists tools and calls them

## Install

```bash
pip install "mcp[cli]"
```

## Run the server

```bash
python3 server.py
```

The server starts a Streamable HTTP endpoint at `http://localhost:8000/mcp` by default.

## Run the agent (client)

List tools:

```bash
python3 agent.py --list-tools
```

Run the demo calls:

```bash
python3 agent.py --demo
```

Call a tool directly:

```bash
python3 agent.py --tool add --args '{"a": 2, "b": 3}'
```

## Customize

- Add tools/resources in `server.py` using `@mcp.tool()` and `@mcp.resource()`.
- Point the agent to another MCP server with `--server-url`.
