"""Generate a secret-free Cursor MCP config for the currently deployed ready agents."""
import argparse
import json
import sys
from pathlib import Path

import httpx
from databricks.sdk import WorkspaceClient

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',default='fevm')
    parser.add_argument('--url',default='https://research-memory-poc-7474653807068368.aws.databricksapps.com')
    parser.add_argument('--output',default=str(ROOT/'cursor-mcp.json'))
    args=parser.parse_args()
    w=WorkspaceClient(profile=args.profile)
    response=httpx.get(args.url.rstrip('/')+'/api/agents',headers=w.config.authenticate(),timeout=60)
    response.raise_for_status()
    servers={}
    for agent in response.json():
        servers['research-'+agent['id']]={
            'command':sys.executable,
            'args':[str(ROOT/'scripts/cursor_mcp.py'),'--profile',args.profile,'--url',args.url,'--agent',agent['id']],
            'env':{'DATABRICKS_AUTH_STORAGE':'plaintext'},
        }
    Path(args.output).write_text(json.dumps({'mcpServers':servers},indent=2)+'\n')
    print(f'Wrote {len(servers)} agent connections to {args.output}')
