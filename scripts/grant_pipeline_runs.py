import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_memory import client,call,resources,CONFIG
def grant_runs():
    cfg=resources()
    for agent,row in cfg.items():
        job=row.get('job_id')
        if not job:
            result=call('POST',f"memory-pipelines/{row['pipeline']}/run",{})
            run=result['name'].split('/')[-1]
            job=client().jobs.get_run(run_id=int(run)).job_id
        client().api_client.do('PATCH',f'/api/2.0/permissions/jobs/{job}',body={'access_control_list':[{'service_principal_name':'74f4837a-b401-4ec6-8277-40cb7dcd303c','permission_level':'CAN_MANAGE_RUN'}]})
        row['job_id']=job
        CONFIG.write_text(json.dumps(cfg,indent=2))
        print(agent,job,'CAN_MANAGE_RUN granted',flush=True)

if __name__=='__main__': grant_runs()
