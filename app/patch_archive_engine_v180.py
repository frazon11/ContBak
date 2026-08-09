from pathlib import Path

path=Path('/app/main.py')
source=path.read_text(encoding='utf-8')

# Replace persistent-data backup with Docker's archive API. This reads the
# filesystem exactly as the target container sees it and therefore does not
# depend on re-mounting NAS/DSM host paths into helper containers.
start=source.index('def backup_container(')
end=source.index('def backup_path(',start)
new_backup=r'''def backup_container(container_id,stop:Optional[bool]=None,progress=None,include_config:bool=True,selected_mounts=None):
 import gzip
 import stat as statmod
 with lock:
  started=datetime.now().isoformat(timespec='seconds'); c=client.containers.get(container_id); info=container_info(c)
  was_running=c.status=='running'; should_stop=STOP_DEFAULT if stop is None else stop
  selected=None if selected_mounts is None else set(selected_mounts)
  info['container_config_included']=bool(include_config)
  info['backup_selection']={'container_config':bool(include_config),'selected_mounts':sorted(selected) if selected is not None else 'all'}
  info['backup_engine']='docker-archive-api'
  details=[]
  def detail(state,m,text):
   line=f"[{state}] {_mount_description(m)} | {text}"
   details.append(line);print(f'[backup] {c.name}: {line}',flush=True)
  if progress:progress(3,f'Preparing container {c.name}…')
  stamp=datetime.now().strftime('%Y-%m-%d_%H-%M-%S');target_rel=f'{safe(c.name)}/{stamp}';target=BACKUP_ROOT/target_rel;target.mkdir(parents=True,exist_ok=True)
  try:
   if include_config:
    if progress:progress(8,'Saving container configuration…')
    (target/'container-inspect.json').write_text(json.dumps(c.attrs,indent=2),encoding='utf-8')
   elif progress:progress(8,'Container configuration excluded by user.')
   if was_running and should_stop:
    if progress:progress(12,'Stopping container for a consistent filesystem snapshot…')
    c.stop(timeout=30);c.reload()
   backed_up=0;skipped=0;excluded=0;failed=0
   mounts=info.get('mounts') or [];total=max(1,len(mounts))
   for i,m in enumerate(mounts):
    destination=m.get('destination','')
    if progress:progress(15+int((i/total)*70),f"Mount {i+1}/{len(mounts)}: {destination}")
    skip_reason=pseudo_or_special_mount(m)
    mount_type=(m.get('type') or '').lower()
    if not skip_reason and mount_type not in ('bind','volume'):
     skip_reason=f"Mount type '{mount_type or 'unknown'}' is not a persistent bind mount or named volume."
    if skip_reason:
     m['archive']=None;m['archive_type']='skipped';m['archive_engine']=None;m['skipped_reason']=skip_reason;skipped+=1;detail('SKIPPED',m,skip_reason);continue
    if selected is not None and destination not in selected:
     reason='Excluded from this backup by user.'
     m['archive']=None;m['archive_type']='excluded';m['archive_engine']=None;m['skipped_reason']=reason;excluded+=1;detail('EXCLUDED',m,reason);continue
    archive=f"mount_{i:02d}_{safe(Path(destination).name or 'root')}.tar.gz"
    try:
     stream,stat_info=c.get_archive(destination)
     mode=int((stat_info or {}).get('mode') or 0)
     archive_type='file' if statmod.S_ISREG(mode) else 'directory'
     archive_path=target/archive
     with gzip.open(archive_path,'wb',compresslevel=6) as gz:
      for chunk in stream:
       if chunk:gz.write(chunk)
     if not archive_path.is_file() or archive_path.stat().st_size<=0:
      raise RuntimeError('Docker archive API returned an empty archive.')
     m['archive']=archive;m['archive_type']=archive_type;m['archive_engine']='docker-archive-api';m['archive_stat']=stat_info or {}
     m['archive_source_path']=destination
     backed_up+=1
     detail('BACKED UP',m,f"Docker archive API; archive={archive}, size={archive_path.stat().st_size} bytes")
    except Exception as mount_error:
     reason=f'Docker archive API failed for container path {destination}: {mount_error}'
     m['archive']=None;m['archive_type']='error';m['archive_engine']='docker-archive-api';m['skipped_reason']=reason;failed+=1;detail('FAILED',m,reason)
   if progress:progress(88,'Saving manifest…')
   (target/'manifest.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
   if progress:progress(93,'Pruning old backups…')
   prune(BACKUP_ROOT/safe(c.name))
   if failed>0:status='error'
   elif skipped>0 or excluded>0 or not include_config:status='warning'
   else:status='success'
   summary=f"{backed_up} backed up, {excluded} excluded, {skipped} skipped, {failed} failed; container config: {'yes' if include_config else 'no'}"
   message=summary+('\n'+'\n'.join(details) if details else '\n[INFO] Container has no mounts.')
   add_run(c.name,started,status,message,str(target))
   if progress:progress(100,summary)
   return {'status':status,'summary':summary,'path':str(target),'details':list(details)}
  except Exception as exc:
   add_run(c.name,started,'error',str(exc),str(target));raise
  finally:
   if was_running and should_stop:
    try:c.start()
    except Exception as restart_error:print(f'[backup] {c.name}: container restart failed: {restart_error}',flush=True)


'''
source=source[:start]+new_backup+source[end:]

# Replace only the final restore execution. Container recreation remains based
# on container-inspect.json, but persistent data is written through Docker's
# archive API into the target container mount namespace. No helper mounts are
# used for backup or restore data transfer.
start=source.index('def restore_backup(')
end=source.index('\ndef scheduled_backup',start)
new_restore=r'''def restore_backup(rel_path,mode='auto',target_name=None,conflict='abort'):
 import gzip
 import posixpath
 import shutil
 import tempfile
 with lock:
  started=datetime.now().isoformat(timespec='seconds')
  target=backup_path(rel_path)
  manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
  original_name=manifest.get('name') or manifest.get('container_name') or 'unknown'
  log_name=target_name or original_name
  steps=[]
  def restore_step(message,status='running'):
   steps.append(str(message));_restore_log(log_name,started,target,message,status)
  try:
   restore_step(f"Restore requested from '{rel_path}' using mode '{mode}'.")
   c=None;created=False
   if mode in ('existing','auto'):
    for candidate in (target_name,manifest.get('id'),original_name):
     if not candidate:continue
     try:c=client.containers.get(candidate);break
     except Exception:pass
   if c:
    restore_step(f"Target container resolved: {c.name}.")
   elif mode in ('recreate','auto'):
    requested_name=(target_name or original_name).strip()
    if not requested_name or requested_name=='unknown':raise RuntimeError('No target container name is available for recreation.')
    c,requested_name=_create_container_from_backup(target,manifest,requested_name,conflict,restore_step)
    log_name=requested_name;created=True
   else:
    raise RuntimeError(f"Target container '{target_name or original_name}' was not found. Select Recreate missing container to restore it from the backup metadata.")

   c.reload();was_running=c.status=='running'
   mounted={m.get('Destination') for m in c.attrs.get('Mounts',[]) if m.get('Destination')}
   restorable=[m for m in manifest.get('mounts',[]) if m.get('archive')]
   for m in restorable:
    destination=m.get('destination');archive=m.get('archive')
    if not destination:raise RuntimeError(f"Backup archive '{archive}' has no destination path in manifest.json.")
    if destination not in mounted:raise RuntimeError(f"Target container has no persistent mount at '{destination}'.")
    if not (target/archive).is_file():raise RuntimeError(f"Archive is missing: {archive}")
   restore_step(f"Preflight passed for {len(restorable)} persistent mount archive(s). Data engine: Docker archive API.")

   if was_running:
    restore_step(f"Stopping container '{c.name}' for restore.");c.stop(timeout=30);c.reload()
   restored=[];restore_error=None;restart_error=None
   try:
    for index,m in enumerate(restorable,1):
     destination=m.get('destination');archive=m.get('archive');archive_file=target/archive
     engine=m.get('archive_engine')
     archive_type=m.get('archive_type','directory')
     # New Docker-API backups contain the destination basename and therefore
     # extract into its parent. Legacy directory archives contain only the
     # directory contents and extract directly into the mount destination.
     if engine=='docker-archive-api':
      clean_dest=destination.rstrip('/') or '/'
      put_path=posixpath.dirname(clean_dest) or '/'
     elif archive_type=='directory':
      put_path=destination
     else:
      raise RuntimeError(f"Legacy regular-file archive '{archive}' cannot be restored safely by the Docker archive engine. Create a new backup with ContBak 1.8.0 or newer.")
     restore_step(f"Restoring {index}/{len(restorable)}: {destination} from {archive} via Docker archive API.")
     try:
      with gzip.open(archive_file,'rb') as gz, tempfile.SpooledTemporaryFile(max_size=128*1024*1024) as tar_stream:
       shutil.copyfileobj(gz,tar_stream,length=1024*1024)
       tar_stream.seek(0)
       result=c.put_archive(put_path,tar_stream)
       if result is False:raise RuntimeError('Docker put_archive returned false.')
     except Exception as exc:
      raise RuntimeError(f"Docker archive restore failed for '{destination}' from '{archive}': {exc}") from exc
     restored.append(destination);restore_step(f"Restored '{destination}' successfully via Docker archive API.")
   except Exception as exc:restore_error=exc
   finally:
    if was_running or created:
     try:restore_step(f"Starting container '{c.name}'.");c.start();restore_step(f"Container '{c.name}' started.")
     except Exception as exc:restart_error=exc
   if restore_error and restart_error:raise RuntimeError(f'{restore_error} Additionally, container start failed: {restart_error}')
   if restore_error:raise restore_error
   if restart_error:raise RuntimeError(f"Data was restored, but container '{c.name}' could not be started: {restart_error}")
   if restorable:
    message=f"Restore completed: container '{c.name}' is available and {len(restored)} persistent mount(s) were restored via Docker archive API."
   else:
    message=f"Restore completed: container '{c.name}' is available. This was a configuration-only backup with no persistent mount archives."
   restore_step(message,'success')
   return {'container':c.name,'created':created,'restored_mounts':restored,'message':message,'steps':steps}
  except Exception as exc:
   detail=f'Restore failed: {exc}';_restore_log(log_name,started,target,detail,'error');raise
'''
source=source[:start]+new_restore+source[end:]
path.write_text(source,encoding='utf-8')
