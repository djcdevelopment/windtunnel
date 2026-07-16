"""End-to-end checkpoint: prove a real MCP client can call the gateway.

Run with the gateway already listening on :8710. Expected output: a list of
five tools, then a status dict with "hearth": "burning".
"""
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    async with streamablehttp_client("http://127.0.0.1:8710/mcp") as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print("tools:", [t.name for t in tools.tools])
            result = await s.call_tool("hearth_status", {})
            print("status:", result.content[0].text)


asyncio.run(main())
