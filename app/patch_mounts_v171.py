from pathlib import Path

path=Path('/app/main.py')
source=path.read_text(encoding='utf-8')

# Replace the final backup implementation after all older patches have run.
start=source.index('def backup_container(')
end=source.index('\n\n\ndef backup_path',start)
new_backup=r'''def _backup_mount_spec(m, bind_to='/source', mode='ro'):
 mount_type=(m.get('type') or '').lower()
 if mount_type=='volume':
  volume_name=m.get('name')
  if not volume_name:
   raise RuntimeError(f"Named volume for '{m.get('destination')}' has no Docker volume name.")
  return {volume_name:{'bind':bind_to,'mode':mode}}
 if mount_type=='bind':
  source_path=m.get('source')
  if not source_path:
   raise RuntimeError(f"Bind mount for '{m.get('destination')}' has no source path.")
  return {source_path:{'bind':bind_to,'mode':mode}}
 raise RuntimeError(f"Mount type '{mount_type or 'unknown'}' is not supported for data backup.")


def _mount_description(m):
 return f"type={m.get('type') or 'unknown'} source={m.get('source') or '-'} name={m.get('name') or '-'} -> {m.get('destination') or '-'}"


def backup_container(container_id,stop:Optional[bool]=None,progress=None,include_config:bool=True,selected_mounts=None):
 with lock:
  started=datetime.now().isoformat(timespec='seconds'); c=client.containers.get(container_id); info=container_info(c)
  was_running=c.status=='running'; should_stop=STOP_DEFAULT if stop is None else stop
  selected=None if selected_mounts is None else set(selected_mounts)
  info['container_config_included']=bool(include_config)
  info['backup_selection']={'container_config':bool(include_config),'selected_mounts':sorted(selected) if selected is not None else 'all'}
  details=[]
  def detail(state,m,text):
   line=f"[{state}] {_mount_description(m)} | {text}"
   details.append(line);print(f'[backup] {c.name}: {line}',flush=True)
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
    archive=f"mount_{i:02d}_{safe(Path(destination).name or 'root')}.tar.gz"
    skip_reason=pseudo_or_special_mount(m)
    if not skip_reason and (m.get('type') or '').lower() not in ('bind','volume'):
     skip_reason=f"Mount type '{m.get('type') or 'unknown'}' is not a persistent bind mount or named volume."
    if skip_reason:
     m['archive']=None;m['archive_type']='skipped';m['skipped_reason']=skip_reason;skipped+=1;detail('SKIPPED',m,skip_reason);continue
    if selected is not None and destination not in selected:
     reason='Excluded from this backup by user.'
     m['archive']=None;m['archive_type']='excluded';m['skipped_reason']=reason;excluded+=1;detail('EXCLUDED',m,reason);continue
    try:
     mounts_for_helper=_backup_mount_spec(m,'/source','ro')
     mounts_for_helper.update({str(host_backup_root()):{'bind':'/backup','mode':'rw'}})
     result=run_helper(mounts_for_helper,
      f"if [ -d /source ]; then tar -C /source -czf /backup/{target_rel}/{archive} . && printf directory; "
      f"elif [ -f /source ]; then tar -C / -czf /backup/{target_rel}/{archive} source && printf file; "
      f"else printf special; fi").strip()
     if result=='directory':
      m['archive']=archive;m['archive_type']='directory';backed_up+=1
      size=(target/archive).stat().st_size if (target/archive).is_file() else 0
      detail('BACKED UP',m,f"archive={archive}, size={size} bytes")
     elif result=='file':
      m['archive']=archive;m['archive_type']='file';backed_up+=1
      size=(target/archive).stat().st_size if (target/archive).is_file() else 0
      detail('BACKED UP',m,f"archive={archive}, size={size} bytes")
     else:
      reason='Mounted source is neither a directory nor a regular file inside the backup helper.'
      m['archive']=None;m['archive_type']='special';m['skipped_reason']=reason;skipped+=1;detail('SKIPPED',m,reason)
    except Exception as mount_error:
     m['archive']=None;m['archive_type']='error';m['skipped_reason']=str(mount_error);failed+=1;detail('FAILED',m,str(mount_error))
   if progress:progress(88,'Saving manifest…')
   (target/'manifest.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
   if progress:progress(93,'Pruning old backups…')
   prune(BACKUP_ROOT/safe(c.name))
   status='success' if failed==0 else 'warning'
   summary=f"{backed_up} backed up, {excluded} excluded, {skipped} skipped, {failed} failed; container config: {'yes' if include_config else 'no'}"
   message=summary + ('\n' + '\n'.join(details) if details else '\n[INFO] Container has no mounts.')
   add_run(c.name,started,status,message,str(target))
   if progress:progress(97,summary)
  except Exception as e:add_run(c.name,started,'error',str(e),str(target));raise
  finally:
   if was_running and should_stop:
    try:
     if progress:progress(99,'Restarting container…')
     c.start()
    except Exception as restart_error:
     print(f'[backup] {c.name}: container restart failed: {restart_error}',flush=True)
'''
source=source[:start]+new_backup+source[end:]

# Improve final restore implementation to use Docker volume names for named volumes.
needle="current_mounts={m.get('Destination'):{'source':m.get('Source'),'type':m.get('Type')} for m in c.attrs.get('Mounts',[]) if m.get('Destination') and m.get('Source')}"
replacement="current_mounts={m.get('Destination'):{'source':m.get('Source'),'type':m.get('Type'),'name':m.get('Name')} for m in c.attrs.get('Mounts',[]) if m.get('Destination') and (m.get('Source') or m.get('Name'))}"
if needle not in source:raise SystemExit('1.7.1: current_mounts pattern not found')
source=source.replace(needle,replacement,1)

old="""    current_source=current.get('source')
    check='set -eu; test -f /target; test -w /target' if archive_type=='file' else 'set -eu; mkdir -p /target; test -d /target; test -w /target'
    try:run_helper({current_source:{'bind':'/target','mode':'rw'}},check)
    except Exception as exc:raise RuntimeError(f\"Preflight failed for '{destination}' at '{current_source}': {exc}\") from exc
    prepared.append((index,m,current_source));restore_step(f\"Preflight passed for '{destination}'.\")
"""
new="""    current_source=current.get('source'); current_type=(current.get('type') or '').lower(); current_name=current.get('name')
    if current_type=='volume':
     if not current_name:raise RuntimeError(f\"Named volume at '{destination}' has no Docker volume name.\")
     restore_mount_key=current_name
    elif current_type=='bind':restore_mount_key=current_source
    else:raise RuntimeError(f\"Restore target '{destination}' uses unsupported mount type '{current_type or 'unknown'}'.\")
    check='set -eu; test -f /target; test -w /target' if archive_type=='file' else 'set -eu; mkdir -p /target; test -d /target; test -w /target'
    restore_step(f\"Preflight {index}/{len(restorable)}: type={current_type}, source={current_source or '-'}, name={current_name or '-'} -> {destination}; archive={archive}.\")
    try:run_helper({restore_mount_key:{'bind':'/target','mode':'rw'}},check)
    except Exception as exc:raise RuntimeError(f\"Preflight failed for '{destination}' ({current_type}, {restore_mount_key}): {exc}\") from exc
    prepared.append((index,m,restore_mount_key,current_type,current_source,current_name));restore_step(f\"Preflight passed for '{destination}'.\")
"""
if old not in source:raise SystemExit('1.7.1: restore preflight pattern not found')
source=source.replace(old,new,1)

old_loop="""    for index,m,current_source in prepared:
     destination=m.get('destination');archive=m.get('archive');archive_type=m.get('archive_type','directory')
     restore_step(f\"Restoring '{destination}' from '{archive}'.\")
     command=f\"set -eu; tar -xOzf /backup/{rel}/{archive} source > /target\" if archive_type=='file' else f\"set -eu; mkdir -p /target; find /target -mindepth 1 -maxdepth 1 -exec rm -rf -- {{}} +; tar -C /target -xzf /backup/{rel}/{archive}\"
     try:run_helper({current_source:{'bind':'/target','mode':'rw'},str(host_backup_root()):{'bind':'/backup','mode':'ro'}},command)
     except Exception as exc:raise RuntimeError(f\"Restore failed for '{destination}' from '{archive}': {exc}\") from exc
     restored.append(destination);restore_step(f\"Restored '{destination}'.\")
"""
new_loop="""    for index,m,restore_mount_key,current_type,current_source,current_name in prepared:
     destination=m.get('destination');archive=m.get('archive');archive_type=m.get('archive_type','directory')
     restore_step(f\"Restoring {index}/{len(prepared)}: type={current_type}, source={current_source or '-'}, name={current_name or '-'} -> {destination} from {archive}.\")
     command=f\"set -eu; tar -xOzf /backup/{rel}/{archive} source > /target\" if archive_type=='file' else f\"set -eu; mkdir -p /target; find /target -mindepth 1 -maxdepth 1 -exec rm -rf -- {{}} +; tar -C /target -xzf /backup/{rel}/{archive}\"
     try:run_helper({restore_mount_key:{'bind':'/target','mode':'rw'},str(host_backup_root()):{'bind':'/backup','mode':'ro'}},command)
     except Exception as exc:raise RuntimeError(f\"Restore failed for '{destination}' ({current_type}, {restore_mount_key}) from '{archive}': {exc}\") from exc
     restored.append(destination);restore_step(f\"Restored '{destination}' successfully.\")
"""
if old_loop not in source:raise SystemExit('1.7.1: restore loop pattern not found')
source=source.replace(old_loop,new_loop,1)

path.write_text(source,encoding='utf-8')
