"""Serverless scheduled task. Uses the job identity and the deployed Lakebase journal."""
import argparse
import json
import os
import sys
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--date',default='')
parser.add_argument('--agent',default='')
parser.add_argument('--source-root',default='')
args=parser.parse_args()
ROOT=Path(args.source_root) if args.source_root else Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['AGENT_JOB_RUNTIME']='1'
settings=json.loads((ROOT/'app.yaml').read_text())
for env in settings['env']:
    if env['name'] in ('LAKEBASE_HOST','LAKEBASE_DB','LAKEBASE_ENDPOINT','AI_GATEWAY_URL','SERVING_ENDPOINT'):
        os.environ[env['name']]=env['value']
# The scheduled job uses its own identity, never the app principal's database username.
os.environ.pop('LAKEBASE_USER',None)

from daily_updates import generate
print(json.dumps(generate(args.date or None,args.agent or None),indent=2))
