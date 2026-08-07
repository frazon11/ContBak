from pathlib import Path

path=Path('/app/main.py')
source=path.read_text(encoding='utf-8')

new_jobs='''def run_backup_job(job_id,container_id,stop,include_config=True,selected_mounts=None):
 try:
  backup_container(container_id,stop,lambda p,m:job_progress(job_id,p,m),include_config=include_config,selected_mounts=selected_mounts)
  job_progress(job_id,100,'Backup completed successfully.','success')
 except Exception as exc:
  update_job(job_id,status='error',message=str(exc),error=str(exc),progress=100)

def start_backup_job(container_id,stop,include_config=True,selected_mounts=None):
 c=client.containers.get(container_id)
 job_id=uuid.uuid4().hex
 with job_lock:
  active_jobs[job_id]={'id':job_id,'container_id':container_id,'container_name':c.name,'status':'queued','progress':0,'message':'Preparing backup…','error':None,'log':[{'time':datetime.now().strftime('%H:%M:%S'),'message':'Backup requested.'}]}
 threading.Thread(target=run_backup_job,args=(job_id,container_id,stop,include_config,selected_mounts),daemon=True,name=f'backup-{job_id[:8]}').start()
 return active_jobs[job_id].copy()
'''

new_backup=r'''def backup_container(container_id,stop:Optional[bool]=None,progress=None,include_config:bool=True,selected_mounts=None):
 with lock:
  started=datetime.now().isoformat(timespec='seconds'); c=client.containers.get(container_id); info=container_info(c)
  was_running=c.status=='running'; should_stop=STOP_DEFAULT if stop is None else stop
  selected=None if selected_mounts is None else set(selected_mounts)
  info['container_config_included']=bool(include_config)
  info['backup_selection']={'container_config':bool(include_config),'selected_mounts':sorted(selected) if selected is not None else 'all'}
  if progress:progress(3,f'Preparing container {c.name}…')
  stamp=datetime.now().strftime('%Y-%m-%d_%H-%M-%S'); target_rel=f'{safe(c.name)}/{stamp}'; target=BACKUP_ROOT/target_rel; target.mkdir(parents=True,exist_ok=True)
  try:
   if was_running and should_stop:
    if progress:progress(8,'Stopping container…')
    c.stop(timeout=30)
   if include_config:
    if progress:progress(12,'Saving container configuration…')
    (target/'container-inspect.json').write_text(json.dumps(c.attrs,indent=2),encoding='utf-8')
   elif progress:progress(12,'Container configuration excluded by user.')
   backed_up=0; skipped=0; excluded=0; failed=0
   mounts=info['mounts']; total=max(1,len(mounts))
   for i,m in enumerate(mounts):
    destination=m.get('destination','')
    if progress:progress(15 + int((i/total)*70),f"Mount {i+1}/{len(mounts)} checking: {destination}")
    archive=f"mount_{i:02d}_{safe(Path(destination).name or 'root')}.tar.gz"; source_path=m['source']
    skip_reason=pseudo_or_special_mount(m)
    if skip_reason:
     m['archive']=None;m['archive_type']='skipped';m['skipped_reason']=skip_reason;skipped+=1;continue
    if selected is not None and destination not in selected:
     m['archive']=None;m['archive_type']='excluded';m['skipped_reason']='Excluded from this backup by user.';excluded+=1;continue
    try:
     result=run_helper(
      {source_path:{'bind':'/source','mode':'ro'},str(host_backup_root()):{'bind':'/backup','mode':'rw'}},
      f"if [ -d /source ]; then tar -C /source -czf /backup/{target_rel}/{archive} . && printf directory; "
      f"elif [ -f /source ]; then tar -C / -czf /backup/{target_rel}/{archive} source && printf file; "
      f"else printf special; fi"
     ).strip()
     if result=='directory':m['archive']=archive;m['archive_type']='directory';backed_up+=1
     elif result=='file':m['archive']=archive;m['archive_type']='file';backed_up+=1
     else:m['archive']=None;m['archive_type']='special';m['skipped_reason']='Mount is neither a directory nor a regular file.';skipped+=1
    except Exception as mount_error:
     m['archive']=None;m['archive_type']='error';m['skipped_reason']=str(mount_error);failed+=1
   if progress:progress(88,'Saving manifest…')
   (target/'manifest.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
   if progress:progress(93,'Pruning old backups…')
   prune(BACKUP_ROOT/safe(c.name))
   status='success' if failed==0 else 'warning'
   message=f"{backed_up} backed up, {excluded} excluded, {skipped} skipped, {failed} failed; container config: {'yes' if include_config else 'no'}"
   add_run(c.name,started,status,message,str(target))
   if progress:progress(97,message)
  except Exception as e:add_run(c.name,started,'error',str(e),str(target));raise
  finally:
   if was_running and should_stop:
    try:
     if progress:progress(99,'Restarting container…')
     c.start()
    except Exception:pass
'''

new_api='''@app.get('/api/backup-info/{container_id}')
def api_backup_info(request:Request,container_id:str):
 auth(request)
 try:
  c=client.containers.get(container_id);info=container_info(c);mounts=[]
  for m in info.get('mounts',[]):
   reason=pseudo_or_special_mount(m)
   mounts.append({**m,'eligible':reason is None,'skip_reason':reason})
  return JSONResponse({'id':c.id,'name':c.name,'image':info.get('image'),'mounts':mounts,'stop_default':STOP_DEFAULT,'container_config':True})
 except Exception as exc:return JSONResponse({'error':str(exc)},status_code=400)

@app.post('/api/backup/{container_id}')
def api_backup_one(request:Request,container_id:str,stop:Optional[str]=Form(None),include_config:Optional[str]=Form('on'),mounts_json:Optional[str]=Form(None)):
 auth(request)
 try:
  selected=None
  if mounts_json is not None:
   raw=json.loads(mounts_json)
   if not isinstance(raw,list) or not all(isinstance(x,str) for x in raw):raise ValueError('Invalid mount selection.')
   selected=raw
  return JSONResponse(start_backup_job(container_id,stop=='on',include_config=='on',selected),status_code=202)
 except Exception as exc:return JSONResponse({'error':str(exc)},status_code=400)
'''

new_sync="""@app.post('/backup/{container_id}')
def backup_one(request:Request,container_id:str,stop:Optional[str]=Form(None),include_config:Optional[str]=Form('on'),mounts_json:Optional[str]=Form(None)):
 auth(request)
 selected=None if mounts_json is None else json.loads(mounts_json)
 backup_container(container_id,stop=='on',include_config=include_config=='on',selected_mounts=selected)
 return RedirectResponse('/',303)
"""

def replace_region(text,start_marker,end_marker,replacement,label):
 try:
  start=text.index(start_marker)
  end=text.index(end_marker,start)
 except ValueError as exc:
  raise SystemExit(f'ContBak 1.7.0 patch: {label} boundary not found; refusing unsafe patch.') from exc
 return text[:start]+replacement+text[end:]

source=replace_region(source,'def run_backup_job(', '\ndef db_conn',new_jobs,'backup job functions')
source=replace_region(source,'def backup_container(', '\ndef backup_path',new_backup,'backup_container function')
source=replace_region(source,"@app.post('/api/backup/{container_id}')", "\n@app.get('/api/jobs/{job_id}')",new_api,'backup API endpoints')
source=replace_region(source,"@app.post('/backup/{container_id}')", "\n@app.post('/backup-all')",new_sync,'synchronous backup endpoint')

path.write_text(source,encoding='utf-8')
