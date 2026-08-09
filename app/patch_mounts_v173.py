from pathlib import Path

path=Path('/app/main.py')
source=path.read_text(encoding='utf-8')

# Return the real backup result to the async job wrapper.
old="""   add_run(c.name,started,status,message,str(target))
   if progress:progress(100,summary)
  except Exception as e:add_run(c.name,started,'error',str(e),str(target));raise
"""
new="""   add_run(c.name,started,status,message,str(target))
   if progress:progress(100,summary)
   return {'status':status,'summary':summary,'path':str(target)}
  except Exception as e:add_run(c.name,started,'error',str(e),str(target));raise
"""
if old not in source: raise SystemExit('1.7.3: backup return pattern not found')
source=source.replace(old,new,1)

# Async jobs must preserve success/warning/error instead of forcing success.
old="""def run_backup_job(job_id,container_id,stop,include_config=True,selected_mounts=None):
 try:
  backup_container(container_id,stop,lambda p,m:job_progress(job_id,p,m),include_config=include_config,selected_mounts=selected_mounts)
  job_progress(job_id,100,'Backup completed successfully.','success')
 except Exception as exc:
  update_job(job_id,status='error',message=str(exc),error=str(exc),progress=100)
"""
new="""def run_backup_job(job_id,container_id,stop,include_config=True,selected_mounts=None):
 try:
  result=backup_container(container_id,stop,lambda p,m:job_progress(job_id,p,m),include_config=include_config,selected_mounts=selected_mounts) or {}
  status=result.get('status','error')
  summary=result.get('summary','Backup finished without a result summary.')
  update_job(job_id,status=status,message=summary,error=None if status!='error' else summary,progress=100)
 except Exception as exc:
  update_job(job_id,status='error',message=str(exc),error=str(exc),progress=100)
"""
if old not in source: raise SystemExit('1.7.3: run_backup_job pattern not found')
source=source.replace(old,new,1)

# Replace the single-strategy inherited-mount backup with a diagnostic dual strategy.
old="""     # Inherit the target container's real mounts. Do not re-bind the host
     # Source path: on NAS platforms Docker's host path may not be safely
     # re-addressable from a second helper container.
     qdest=__import__('shlex').quote(destination)
     helper_volumes={str(host_backup_root()):{'bind':'/backup','mode':'rw'}}
     result=run_helper(helper_volumes,
      f\"if [ -d {qdest} ]; then tar -C {qdest} -czf /backup/{target_rel}/{archive} . && printf directory; \"
      f\"elif [ -f {qdest} ]; then parent=$(dirname {qdest}); base=$(basename {qdest}); tar -C \\\"$parent\\\" -czf /backup/{target_rel}/{archive} \\\"$base\\\" && printf file; \"
      f\"else printf special; fi\",volumes_from=[c.id+':ro']).strip()
"""
new="""     # Strategy 1: inherit the exact mount view of the target container.
     # Strategy 2: fall back to Docker's host bind/volume addressing. A normal
     # bind/volume that is inaccessible by both strategies is a FAILED backup,
     # never a SKIPPED backup.
     qdest=__import__('shlex').quote(destination)
     probe_cmd=f\"if [ -d {qdest} ]; then printf directory; elif [ -f {qdest} ]; then printf file; elif [ -e {qdest} ]; then printf special; else printf missing; fi; printf '|'; stat -c 'type=%F mode=%a uid=%u gid=%g' {qdest} 2>&1 || true\"
     inherited_diag=run_helper({},probe_cmd,volumes_from=[c.id+':ro']).strip()
     inherited_kind=inherited_diag.split('|',1)[0]
     result=''
     access_mode=''
     if inherited_kind in ('directory','file'):
      helper_volumes={str(host_backup_root()):{'bind':'/backup','mode':'rw'}}
      if inherited_kind=='directory':
       run_helper(helper_volumes,f\"tar -C {qdest} -czf /backup/{target_rel}/{archive} .\",volumes_from=[c.id+':ro'])
      else:
       run_helper(helper_volumes,f\"parent=$(dirname {qdest}); base=$(basename {qdest}); tar -C \\\"$parent\\\" -czf /backup/{target_rel}/{archive} \\\"$base\\\"\",volumes_from=[c.id+':ro'])
      result=inherited_kind;access_mode='target-container mount view'
     else:
      fallback_volumes=_backup_mount_spec(m,'/source','ro')
      fallback_probe=run_helper(fallback_volumes,\"if [ -d /source ]; then printf directory; elif [ -f /source ]; then printf file; elif [ -e /source ]; then printf special; else printf missing; fi; printf '|'; stat -c 'type=%F mode=%a uid=%u gid=%g' /source 2>&1 || true\").strip()
      fallback_kind=fallback_probe.split('|',1)[0]
      if fallback_kind in ('directory','file'):
       fallback_volumes.update({str(host_backup_root()):{'bind':'/backup','mode':'rw'}})
       if fallback_kind=='directory':
        run_helper(fallback_volumes,f\"tar -C /source -czf /backup/{target_rel}/{archive} .\")
       else:
        run_helper(fallback_volumes,f\"tar -C / -czf /backup/{target_rel}/{archive} source\")
       result=fallback_kind;access_mode='direct Docker mount fallback'
      else:
       raise RuntimeError(f\"Persistent mount is inaccessible. inherited=[{inherited_diag}] fallback=[{fallback_probe}]\")
     detail('ACCESS',m,f\"{access_mode}; inherited=[{inherited_diag}]\")
"""
if old not in source: raise SystemExit('1.7.3: v172 backup strategy pattern not found')
source=source.replace(old,new,1)

# If a supported persistent mount somehow reaches the non-file/non-dir branch,
# classify it as FAILED rather than SKIPPED.
old="""     else:
      reason='Mounted source is neither a directory nor a regular file inside the backup helper.'
      m['archive']=None;m['archive_type']='special';m['skipped_reason']=reason;skipped+=1;detail('SKIPPED',m,reason)
"""
new="""     else:
      reason='Persistent mount could not be resolved as a directory or regular file.'
      m['archive']=None;m['archive_type']='error';m['skipped_reason']=reason;failed+=1;detail('FAILED',m,reason)
"""
if old not in source: raise SystemExit('1.7.3: special persistent mount pattern not found')
source=source.replace(old,new,1)

path.write_text(source,encoding='utf-8')
