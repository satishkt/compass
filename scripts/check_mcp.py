"""Check the deployed MCP protocol and the exact stdio connector used by Cursor."""
import asyncio
import json
import os
import sys
from datetime import timedelta
from pathlib import Path

import httpx
from databricks.sdk import WorkspaceClient
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

ROOT=Path(__file__).resolve().parents[1]
BASE=os.getenv('CHECK_URL','https://research-memory-poc-7474653807068368.aws.databricksapps.com')


async def main():
    w=WorkspaceClient(profile='fevm')
    async with httpx.AsyncClient(headers=w.config.authenticate(),timeout=600) as http:
        response=await http.get(BASE+'/api/agents');response.raise_for_status()
        directory=response.json()
        for agent in directory:
            async with streamable_http_client(BASE+'/mcp/'+agent['id'],http_client=http) as (read,write,_):
                async with ClientSession(read,write) as session:
                    await session.initialize()
                    tools=(await session.list_tools()).tools
                    expected='ask_'+agent['id'].replace('-','_')
                    assert {t.name for t in tools}=={expected,'get_conversation','list_conversations'}
                    print(agent['id'],'MCP discovery passed')
        async with streamable_http_client(BASE+'/mcp/valuation',http_client=http) as (read,write,_):
            async with ClientSession(read,write) as session:
                await session.initialize()
                result=await session.call_tool('ask_valuation',{'question':'What distinguishes an exploratory DCF result from a published fair value?'},read_timeout_seconds=timedelta(seconds=600))
                assert not result.isError, result
                key=result.structuredContent['session_id']
                assert result.structuredContent['agent']=='valuation'
                again=await session.call_tool('ask_valuation',{'question':'Which basis checks must be reviewed first?','session_id':key},read_timeout_seconds=timedelta(seconds=600))
                assert not again.isError and again.structuredContent['session_id']==key
                history=await session.call_tool('get_conversation',{'session_id':key})
                events=history.structuredContent['events']
                assert sum(e['role']=='user' for e in events)==2
                assert sum(e['role']=='assistant' and e['kind']=='message' for e in events)==2
                print('Direct agent answer, continued session and durable journal passed')
        async with streamable_http_client(BASE+'/mcp/portfolio',http_client=http) as (read,write,_):
            async with ClientSession(read,write) as session:
                await session.initialize()
                denied=await session.call_tool('get_conversation',{'session_id':key})
                assert denied.isError
                print('Cross-agent session scope passed')
    params=StdioServerParameters(command=sys.executable,args=[str(ROOT/'scripts/cursor_mcp.py'),'--profile','fevm','--url',BASE,'--agent','valuation'],env=dict(os.environ,DATABRICKS_AUTH_STORAGE='plaintext'))
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            assert 'ask_valuation' in {t.name for t in (await session.list_tools()).tools}
            result=await session.call_tool('list_conversations',{})
            assert not result.isError and key in {c['id'] for c in result.structuredContent['conversations']}
            print('Cursor stdio connector: fevm authentication, discovery and tool call passed')
    (ROOT/'artifacts/mcp-check.json').write_text(json.dumps({'agents':[a['id'] for a in directory],'session_id':key,'checks':['discovery','direct answer','continued session','journal','agent scope','Cursor stdio connector']},indent=2)+'\n')


if __name__=='__main__':
    asyncio.run(main())
