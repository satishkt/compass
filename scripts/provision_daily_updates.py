"""Create the managed archive volume and a daily serverless job; reruns update the same job."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import AlreadyExists,NotFound
from databricks.sdk.service.catalog import VolumeType,PermissionsChange,Privilege

ROOT=Path(__file__).resolve().parents[1]
w=WorkspaceClient(profile='fevm')
deployment=json.loads((ROOT/'deployment.json').read_text())
catalog=deployment['catalog'];schema='agent_memory';volume='daily_updates'
try: w.schemas.get(catalog+'.'+schema)
except NotFound: w.schemas.create(name=schema,catalog_name=catalog,comment='Research agents: per-agent Markdown activity archive')
try: w.volumes.read(catalog+'.'+schema+'.'+volume)
except NotFound: w.volumes.create(catalog,schema,volume,VolumeType.MANAGED,comment='Daily per-agent conversation summaries. Unreviewed activity notes, not approved memory.')
sp=deployment['service_principal']
for kind,name,privilege in [('catalog',catalog,Privilege.USE_CATALOG),('schema',catalog+'.'+schema,Privilege.USE_SCHEMA),('volume',catalog+'.'+schema+'.'+volume,Privilege.READ_VOLUME)]:
    w.grants.update(kind,name,changes=[PermissionsChange(principal=sp,add=[privilege])])
settings={
    'name':'research-memory-daily-updates',
    'description':'Summarize saved conversations per agent, including the supervisor and UI-created agents, into dated Markdown files in a UC volume.',
    'max_concurrent_runs':1,
    'queue':{'enabled':True},
    'schedule':{'quartz_cron_expression':'0 15 0 * * ?','timezone_id':'Asia/Dubai','pause_status':'UNPAUSED'},
    'parameters':[{'name':'date','default':''},{'name':'agent','default':''}],
    'tasks':[{'task_key':'daily_agent_updates','spark_python_task':{'python_file':deployment['workspace_path']+'/scripts/daily_updates_task.py','source':'WORKSPACE','parameters':['--source-root',deployment['workspace_path'],'--date','{{job.parameters.date}}','--agent','{{job.parameters.agent}}']},'environment_key':'summary','max_retries':1,'min_retry_interval_millis':60000,'timeout_seconds':3600}],
    'environments':[{'environment_key':'summary','spec':{'client':'1','dependencies':['databricks-sdk>=0.133','psycopg[binary]>=3.2,<4','httpx>=0.28,<1']}}],
    'tags':{'project':'research-memory-poc','purpose':'daily-conversation-summary'},
}
path=ROOT/'daily-updates.json'
cfg=json.loads(path.read_text()) if path.exists() else {}
job=cfg.get('job_id')
if not job:
    existing=list(w.jobs.list(name=settings['name']))
    job=existing[0].job_id if existing else None
if job: w.api_client.do('POST','/api/2.1/jobs/reset',body={'job_id':job,'new_settings':settings})
else: job=w.api_client.do('POST','/api/2.1/jobs/create',body=settings)['job_id']
w.api_client.do('PATCH',f'/api/2.0/permissions/jobs/{job}',body={'access_control_list':[{'service_principal_name':sp,'permission_level':'CAN_MANAGE_RUN'}]})
cfg={'job_id':job,'volume_root':'/Volumes/'+catalog+'/'+schema+'/'+volume,'timezone':'Asia/Dubai','schedule':'Daily at 00:15 Asia/Dubai, for the previous calendar day','gateway_url':'https://7474653807068368.ai-gateway.cloud.databricks.com/mlflow/v1','model':'system.ai.claude-sonnet-4-6','workspace_host':w.config.host}
path.write_text(json.dumps(cfg,indent=2))
print(json.dumps(cfg,indent=2))
