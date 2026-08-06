from pathlib import Path

path = Path('/app/main.py')
source = path.read_text(encoding='utf-8')

old = '''def restore_backup(rel_path):
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

new = '''def restore_backup(rel_path):
 with lock:
  started=datetime.now().isoformat(timespec='seconds')
  target=backup_path(rel_path)
  manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
  container_name=manifest.get('name') or manifest.get('container_name') or 'unknown'
  steps=[]

  def restore_step(message,status='running'):
   text=str(message)
   steps.append(text)
   print(f'[restore] {container_name}: {text}',flush=True)
   add_run(container_name,started,status,text,str(target))

  try:
   restore_step(f"Restore requested from '{rel_path}'.")
   try:
    c=client.containers.get(manifest.get('id'))
    restore_step(f"Target container resolved by ID: {c.name}.")
   except Exception:
    if not container_name or container_name=='unknown':
     raise RuntimeError('Backup manifest contains neither a usable container ID nor a container name.')
    try:c=client.containers.get(container_name)
    except Exception as exc:
     raise RuntimeError(f"Target container '{container_name}' was not found. Create the container or restore to a container with the recorded name first.") from exc
    restore_step(f"Target container resolved by name: {c.name}.")

   c.reload()
   was_running=c.status=='running'
   current_mounts={
    m.get('Destination'):{'source':m.get('Source'),'type':m.get('Type')}
    for m in c.attrs.get('Mounts',[])
    if m.get('Destination') and m.get('Source')
   }
   restorable=[m for m in manifest.get('mounts',[]) if m.get('archive')]
   if not restorable:
    raise RuntimeError('This backup contains no restorable mount archives.')
   restore_step(f'Preflight started for {len(restorable)} mount(s).')

   prepared=[]
   rel=target.relative_to(BACKUP_ROOT)
   for index,m in enumerate(restorable,1):
    destination=m.get('destination')
    archive=m.get('archive')
    archive_type=m.get('archive_type','directory')
    if not destination:
     raise RuntimeError(f'Mount {index} has no destination in manifest.json.')
    current=current_mounts.get(destination)
    if not current:
     raise RuntimeError(f"Mount {index}/{len(restorable)} cannot be restored: target container has no mount at '{destination}'.")
    current_source=current.get('source')
    mount_type=current.get('type') or 'unknown'
    archive_file=target/archive
    if not archive_file.is_file():
     raise RuntimeError(f"Mount {index}/{len(restorable)} archive is missing: {archive}")

    restore_step(f"Preflight mount {index}/{len(restorable)}: destination='{destination}', type='{mount_type}', source='{current_source}', archive='{archive}', archive_type='{archive_type}'.")
    try:
     if archive_type=='file':
      check='set -eu; test -f /target || { echo "target is not a regular file" >&2; exit 21; }; test -w /target || { echo "target file is not writable" >&2; exit 22; }'
     else:
      check='set -eu; mkdir -p /target; test -d /target || { echo "target is not a directory" >&2; exit 23; }; test -w /target || { echo "target directory is not writable" >&2; exit 24; }'
     run_helper({current_source:{'bind':'/target','mode':'rw'}},check)
    except Exception as exc:
     raise RuntimeError(f"Preflight failed for mount {index}/{len(restorable)} '{destination}'. The target path may be missing, have the wrong type, or be unwritable: {exc}") from exc
    prepared.append((index,m,current_source))
    restore_step(f"Preflight mount {index}/{len(restorable)} passed.")

   if was_running:
    restore_step(f"Stopping container '{c.name}'.")
    c.stop(timeout=30)
    restore_step(f"Container '{c.name}' stopped.")

   restored=[]
   restore_error=None
   restart_error=None
   try:
    for index,m,current_source in prepared:
     destination=m.get('destination')
     archive=m.get('archive')
     archive_type=m.get('archive_type','directory')
     restore_step(f"Restoring mount {index}/{len(prepared)} '{destination}' from '{archive}'.")
     if archive_type=='file':
      command=f"set -eu; tar -xOzf /backup/{rel}/{archive} source > /target"
     else:
      command=f"set -eu; mkdir -p /target; find /target -mindepth 1 -maxdepth 1 -exec rm -rf -- {{}} +; tar -C /target -xzf /backup/{rel}/{archive}"
     try:
      run_helper({current_source:{'bind':'/target','mode':'rw'},str(host_backup_root()):{'bind':'/backup','mode':'ro'}},command)
     except Exception as exc:
      raise RuntimeError(f"Restore failed for mount {index}/{len(prepared)} '{destination}' from '{archive}': {exc}") from exc
     restored.append(destination)
     restore_step(f"Mount {index}/{len(prepared)} '{destination}' restored successfully.")
   except Exception as exc:
    restore_error=exc
   finally:
    if was_running:
     try:
      restore_step(f"Starting container '{c.name}'.")
      c.start()
      restore_step(f"Container '{c.name}' started.")
     except Exception as exc:
      restart_error=exc
      restore_step(f"Container restart failed: {exc}",'error')

   if restore_error and restart_error:
    raise RuntimeError(f'{restore_error} Additionally, container restart failed: {restart_error}')
   if restore_error:raise restore_error
   if restart_error:raise RuntimeError(f"Restore data operation finished, but container '{c.name}' could not be restarted: {restart_error}")

   message=f"Restore completed: {len(restored)} mount(s) restored to {c.name}."
   restore_step(message,'success')
   return {'container':c.name,'restored_mounts':restored,'message':message,'steps':steps}
  except Exception as exc:
   detail=f'Restore failed: {exc}'
   print(f'[restore] {container_name}: {detail}',flush=True)
   add_run(container_name,started,'error',detail,str(target))
   raise
'''

if old not in source:
    raise SystemExit('ContBak 1.5.2 restore function pattern not found; refusing unsafe patch.')

path.write_text(source.replace(old,new,1),encoding='utf-8')
