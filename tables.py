"""Bounded, catalog-scoped query templates. No arbitrary model/user SQL is accepted."""
import os
import re
import time
from datetime import datetime, timezone
from fastapi import HTTPException

IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
def identifier(value):
    if not IDENT.fullmatch(value):
        raise HTTPException(400, 'Use a simple schema, table, or column identifier.')
    return f'`{value}`'

def build_query(op, schema='', table='', column=''):
    catalog = identifier(os.getenv('POC_CATALOG', 'satish_doc_intelligence_catalog'))
    if op == 'schemas':
        return f'SELECT schema_name FROM {catalog}.information_schema.schemata ORDER BY schema_name LIMIT 100'
    s = identifier(schema)
    if op == 'tables':
        return f"SELECT table_name, table_type, comment FROM {catalog}.information_schema.tables WHERE table_schema = '{schema}' ORDER BY table_name LIMIT 100"
    t = identifier(table)
    name = f'{catalog}.{s}.{t}'
    if op == 'describe':
        return f"SELECT column_name, data_type, is_nullable, comment FROM {catalog}.information_schema.columns WHERE table_schema = '{schema}' AND table_name = '{table}' ORDER BY ordinal_position LIMIT 200"
    if op == 'keys':
        return f"SELECT constraint_name, constraint_type FROM {catalog}.information_schema.table_constraints WHERE table_schema = '{schema}' AND table_name = '{table}' LIMIT 100"
    if op == 'count':
        return f'SELECT COUNT(*) AS row_count FROM {name}'
    if op == 'distribution':
        c = identifier(column)
        return f'SELECT {c}, COUNT(*) AS frequency FROM {name} GROUP BY {c} ORDER BY frequency DESC LIMIT 50'
    raise HTTPException(400, 'Unsupported operation.')

def run_query(sql, forwarded_token=None):
    from databricks.sdk import WorkspaceClient
    warehouse = os.getenv('DATABRICKS_WAREHOUSE_ID')
    if not warehouse:
        raise HTTPException(503, 'No SQL warehouse configured. Knowledge chat remains available.')
    if os.getenv('DATABRICKS_APP_NAME'):
        if not forwarded_token:
            raise HTTPException(403, 'End-user authorization is required. Enable sql user authorization on this Databricks App.')
        host = os.environ['DATABRICKS_HOST']
        if not host.startswith('https://'):
            host = 'https://' + host
        w = WorkspaceClient(host=host, token=forwarded_token, auth_type='pat')
    else:
        w = WorkspaceClient(profile=os.getenv('DATABRICKS_CONFIG_PROFILE', 'fevm'))
    # INTERNAL statement execution adapter: fixed query templates only, OBO on deployment.
    result = w.api_client.do('POST', '/api/2.0/sql/statements', body={'warehouse_id': warehouse, 'statement': sql, 'wait_timeout': '10s', 'row_limit': 200, 'byte_limit': 200000, 'on_wait_timeout': 'CONTINUE'})
    statement_id = result['statement_id']
    deadline = time.monotonic() + 45
    while result['status']['state'] in ('PENDING', 'RUNNING'):
        if time.monotonic() > deadline:
            w.api_client.do('POST', f'/api/2.0/sql/statements/{statement_id}/cancel')
            raise HTTPException(504, 'Query timed out and cancellation was requested.')
        time.sleep(.6)
        result = w.api_client.do('GET', f'/api/2.0/sql/statements/{statement_id}')
    if result['status']['state'] != 'SUCCEEDED':
        raise HTTPException(400, result['status'].get('error', {}).get('message', 'Query failed.'))
    return {'sql': sql, 'executed_at': datetime.now(timezone.utc).isoformat(), 'statement_id': statement_id, 'columns': [c['name'] for c in result.get('manifest', {}).get('schema', {}).get('columns', [])], 'rows': result.get('result', {}).get('data_array', []), 'truncated': result.get('manifest', {}).get('truncated', False), 'identity': 'end-user OBO' if forwarded_token else 'local fevm profile'}
