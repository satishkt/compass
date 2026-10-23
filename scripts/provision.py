"""Provision isolated app resources in fevm. Never edits existing research app or tables."""
import json
from pathlib import Path
import psycopg
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import postgres

ROOT = Path(__file__).resolve().parents[1]
w = WorkspaceClient(profile='fevm')
name = 'research-memory-poc'
try:
    app = w.api_client.do('GET', '/api/2.0/apps/' + name)
except Exception as exc:
    if getattr(exc, 'error_code', '') not in ('RESOURCE_DOES_NOT_EXIST', 'NOT_FOUND'):
        raise
    app = w.api_client.do('POST', '/api/2.0/apps', body={
        'name': name, 'description': 'Pipeline Compass: requirements, decisions, and design memory for every reporting pipeline.',
        'user_api_scopes': ['sql'],
        'resources': [{'name': 'knowledge-model', 'serving_endpoint': {'name': 'databricks-claude-sonnet-4-6', 'permission': 'CAN_QUERY'}}]
    })
# Re-fetch in case create returned an operation wrapper.
app = w.api_client.do('GET', '/api/2.0/apps/' + name)
sp = app['service_principal_client_id']
endpoint = 'projects/pmt/branches/production/endpoints/primary'
roles = list(w.postgres.list_roles(parent='projects/pmt/branches/production'))
if not any(r.name and r.name.endswith('/roles/research-memory-poc') for r in roles):
    w.postgres.create_role(parent='projects/pmt/branches/production',role_id='research-memory-poc',role=postgres.Role(spec=postgres.RoleRoleSpec(identity_type=postgres.RoleIdentityType.SERVICE_PRINCIPAL,postgres_role=sp)))
cred = w.api_client.do('POST', '/api/2.0/postgres/credentials', body={'endpoint': endpoint})
host = 'ep-young-pond-d80g7f6r.database.us-east-2.cloud.databricks.com'
from psycopg import sql
with psycopg.connect(host=host, dbname='pmt', user=w.current_user.me().user_name, password=cred['token'], sslmode='require') as db:
    db.execute('CREATE SCHEMA IF NOT EXISTS knowledge_agent')
    db.execute(sql.SQL('GRANT USAGE, CREATE ON SCHEMA knowledge_agent TO {}').format(sql.Identifier(sp)))
    db.execute(sql.SQL('GRANT CONNECT ON DATABASE pmt TO {}').format(sql.Identifier(sp)))
    db.execute(sql.SQL('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA knowledge_agent TO {}').format(sql.Identifier(sp)))
    db.execute(sql.SQL('ALTER DEFAULT PRIVILEGES IN SCHEMA knowledge_agent GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}').format(sql.Identifier(sp)))
# Create the MLflow experiment and resource permissions separately from data permissions.
experiment_name = '/Users/' + w.current_user.me().user_name + '/research-memory-poc'
try:
    exp = w.experiments.get_by_name(experiment_name)
except Exception as exc:
    if getattr(exc, 'error_code', '') != 'RESOURCE_DOES_NOT_EXIST':
        raise
    exp = None
if exp is None:
    exp_id = w.experiments.create_experiment(experiment_name).experiment_id
else:
    exp_id = exp.experiment.experiment_id
w.api_client.do('PATCH', f'/api/2.0/permissions/experiments/{exp_id}', body={'access_control_list': [{'service_principal_name':sp,'permission_level':'CAN_EDIT'}]})
state = {'app':name,'url':app['url'],'service_principal':sp,'experiment_id':exp_id,'workspace_path':'/Workspace/Users/'+w.current_user.me().user_name+'/research-memory-poc-src','catalog':'satish_doc_intelligence_catalog','warehouse':'f7eaba73b2f9c0dc'}
(ROOT/'deployment.json').write_text(json.dumps(state, indent=2))
env = {'MLFLOW_ARTIFACT_UPLOAD_DOWNLOAD_TIMEOUT':'5','MLFLOW_HTTP_REQUEST_MAX_RETRIES':'1','MLFLOW_HTTP_REQUEST_BACKOFF_FACTOR':'1','PUBLIC_APP_URL':app['url'],'POC_CATALOG':state['catalog'],'DATABRICKS_WAREHOUSE_ID':state['warehouse'],'SERVING_ENDPOINT':'system.ai.claude-sonnet-4-6','AI_GATEWAY_URL':'https://7474653807068368.ai-gateway.cloud.databricks.com/mlflow/v1','LAKEBASE_HOST':host,'LAKEBASE_DB':'pmt','LAKEBASE_ENDPOINT':endpoint,'LAKEBASE_USER':sp,'MLFLOW_EXPERIMENT_ID':exp_id}
# JSON is valid YAML, avoiding an extra YAML dependency.
(ROOT/'app.yaml').write_text(json.dumps({'command':['uvicorn','app:app','--host','0.0.0.0','--port','8000'],'env':[{'name':k,'value':str(v)} for k,v in env.items()]},indent=2))
print(json.dumps(state, indent=2))
