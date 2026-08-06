from pathlib import Path

path = Path('/app/main.py')
source = path.read_text(encoding='utf-8')

old_restore = '''def restore_backup(rel_path):
 with lock:
  target=backup_path(rel_path)
  manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8')); c=client.containers.get(manifest['id']); was_running=c.status=='running'
  if was_running:c.stop(timeout=30)
  try:
   for m in manifest['mounts']:
    if not m.get('archive'):continue
    rel=target.relative_to(BACKUP_ROOT); source=m['source']; archive_type=m.get('archive_type','directory')
    if archive_type=='file':
     command=f"tar -xOzf /backup/{rel}/{m['archive']} source > /target"
    else:
     command=f"find /target -mindepth 1 -maxdepth 1 -exec rm -rf -- {{}} +; tar -C /target -xzf /backup/{rel}/{m['archive']}"
    run_helper({source:{'bind':'/target','mode':'rw'},str(host_backup_root()):{'bind':'/backup','mode':'ro'}},command)
  finally:
   if was_running:c.start()
'''

new_restore = '''def restore_backup(rel_path):
 with lock:
  started=datetime.now().isoformat(timespec='seconds')
  target=backup_path(rel_path)
  manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
  container_name=manifest.get('name') or manifest.get('container_name') or 'unknown'
  try:
   try:
    c=client.containers.get(manifest.get('id'))
   except Exception:
    if not container_name or container_name=='unknown':
     raise RuntimeError('Backup manifest contains neither a usable container ID nor a container name.')
    try:c=client.containers.get(container_name)
    except Exception as exc:
     raise RuntimeError(f"Target container '{container_name}' was not found. Create the container or restore to a container with the recorded name first.") from exc

   c.reload()
   was_running=c.status=='running'
   current_mounts={m.get('Destination'):m.get('Source') for m in c.attrs.get('Mounts',[]) if m.get('Destination') and m.get('Source')}
   restorable=[m for m in manifest.get('mounts',[]) if m.get('archive')]
   if not restorable:
    raise RuntimeError('This backup contains no restorable mount archives.')

   if was_running:c.stop(timeout=30)
   restored=[]
   try:
    rel=target.relative_to(BACKUP_ROOT)
    for index,m in enumerate(restorable,1):
     destination=m.get('destination')
     archive=m.get('archive')
     archive_type=m.get('archive_type','directory')
     if not destination:
      raise RuntimeError(f'Mount {index} has no destination in manifest.json.')
     current_source=current_mounts.get(destination)
     if not current_source:
      raise RuntimeError(f"Mount {index}/{len(restorable)} cannot be restored: target container has no mount at '{destination}'.")
     archive_file=target/archive
     if not archive_file.is_file():
      raise RuntimeError(f"Mount {index}/{len(restorable)} archive is missing: {archive}")
     if archive_type=='file':
      command=f"set -eu; tar -xOzf /backup/{rel}/{archive} source > /target"
     else:
      command=f"set -eu; find /target -mindepth 1 -maxdepth 1 -exec rm -rf -- {{}} +; tar -C /target -xzf /backup/{rel}/{archive}"
     try:
      run_helper({current_source:{'bind':'/target','mode':'rw'},str(host_backup_root()):{'bind':'/backup','mode':'ro'}},command)
     except Exception as exc:
      raise RuntimeError(f"Restore failed for mount {index}/{len(restorable)} '{destination}' from '{archive}': {exc}") from exc
     restored.append(destination)
   finally:
    if was_running:
     try:c.start()
     except Exception as exc:
      raise RuntimeError(f"Restore data operation finished, but container '{c.name}' could not be restarted: {exc}") from exc

   message=f"Restore completed: {len(restored)} mount(s) restored to {c.name}."
   add_run(c.name,started,'success',message,str(target))
   return {'container':c.name,'restored_mounts':restored,'message':message}
  except Exception as exc:
   add_run(container_name,started,'error',f'Restore failed: {exc}',str(target))
   raise
'''

old_endpoint = '''@app.post('/restore')
def restore(request:Request,path:str=Form(...)): auth(request); restore_backup(path); return RedirectResponse('/',303)
'''

new_endpoint = '''@app.post('/restore')
def restore(request:Request,path:str=Form(...)):
 auth(request)
 wants_json='application/json' in request.headers.get('accept','').lower()
 try:
  result=restore_backup(path)
  if wants_json:return JSONResponse({'status':'success',**result})
  return RedirectResponse('/?tab=backups&restore=success',303)
 except Exception as exc:
  detail=str(exc) or exc.__class__.__name__
  if wants_json:return JSONResponse({'status':'error','error':detail,'type':exc.__class__.__name__},status_code=400)
  return JSONResponse({'status':'error','error':detail,'type':exc.__class__.__name__},status_code=400)
'''

if old_restore not in source:
    raise SystemExit('Original restore_backup function pattern not found; refusing unsafe patch.')
if old_endpoint not in source:
    raise SystemExit('Original /restore endpoint pattern not found; refusing unsafe patch.')

source = source.replace(old_restore, new_restore, 1)
source = source.replace(old_endpoint, new_endpoint, 1)
path.write_text(source, encoding='utf-8')
