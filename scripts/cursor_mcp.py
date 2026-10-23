"""Cursor stdio connector: refresh fevm OAuth credentials for the deployed MCP endpoint."""
import argparse
import asyncio
import sys
from datetime import timedelta

import httpx
from databricks.sdk import WorkspaceClient
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

DEFAULT_URL = 'https://research-memory-poc-7474653807068368.aws.databricksapps.com'


class ProfileAuth(httpx.Auth):
    def __init__(self, profile):
        self.client = WorkspaceClient(profile=profile)

    def auth_flow(self, request):
        request.headers.update(self.client.config.authenticate())
        yield request


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', default='')
    parser.add_argument('--profile', default='fevm')
    parser.add_argument('--url', default=DEFAULT_URL)
    args = parser.parse_args()
    import re
    if args.agent and not re.fullmatch(r'[a-z][a-z0-9-]{1,39}',args.agent):
        parser.error('Invalid agent ID')
    url = args.url.rstrip('/')+'/mcp/'+args.agent
    proxy = Server('cursor-research-agents')
    async with httpx.AsyncClient(auth=ProfileAuth(args.profile),timeout=httpx.Timeout(600,connect=30),follow_redirects=True) as http:
        async with streamable_http_client(url,http_client=http) as (read,write,_):
            async with ClientSession(read,write) as remote:
                await remote.initialize()

                @proxy.list_tools()
                async def tools() -> list[Tool]:
                    return (await remote.list_tools()).tools

                @proxy.call_tool(validate_input=False)
                async def call(name, arguments):
                    return await remote.call_tool(name,arguments,read_timeout_seconds=timedelta(seconds=600))

                async with stdio_server() as (stdin,stdout):
                    await proxy.run(stdin,stdout,proxy.create_initialization_options())


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
