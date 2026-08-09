from pathlib import Path

path=Path('/app/main.py')
source=path.read_text(encoding='utf-8')

old="""   return {'status':status,'summary':summary,'path':str(target)}
"""
new="""   return {'status':status,'summary':summary,'path':str(target),'details':list(details)}
"""
if old not in source:
 raise SystemExit('1.7.3: backup result details pattern not found')
source=source.replace(old,new,1)

old="""def run_backup_job(job_id,container_id,stop,include_config=True,selected_mounts=None):
 try:
  result=backup_container(container_id,stop,lambda p,m:job_progress(job_id,p,m),include_config=include_config,selected_mounts=selected_mounts) or {}
  status=result.get('status','error')
  summary=result.get('summary','Backup finished without a result summary.')
  update_job(job_id,status=status,message=summary,error=None if status!='error' else summary,progress=100)
 except Exception as exc:
  update_job(job_id,status='error',message=str(exc),error=str(exc),progress=100)
"""
new="""def run_backup_job(job_id,container_id,stop,include_config=True,selected_mounts=None):
 try:
  result=backup_container(container_id,stop,lambda p,m:job_progress(job_id,p,m),include_config=include_config,selected_mounts=selected_mounts) or {}
  status=result.get('status','error')
  summary=result.get('summary','Backup finished without a result summary.')
  # backup_container already sends the summary through progress(100, summary).
  # Add each per-mount diagnostic to the asynchronous job log, then only
  # update terminal state here so the summary is not duplicated.
  for line in result.get('details') or []:
   update_job(job_id,message=line)
  update_job(job_id,status=status,error=None if status!='error' else summary,progress=100)
 except Exception as exc:
  update_job(job_id,status='error',message=str(exc),error=str(exc),progress=100)
"""
if old not in source:
 raise SystemExit('1.7.3: async job detail logging pattern not found')
source=source.replace(old,new,1)

path.write_text(source,encoding='utf-8')
