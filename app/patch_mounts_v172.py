from pathlib import Path

path=Path('/app/main.py')
source=path.read_text(encoding='utf-8')

# Helpers created by Docker should inherit the target container's existing
# mounts instead of trying to re-bind Docker host Source paths. This avoids
# host-path visibility/translation issues (notably on Synology).
old="""def run_helper(volumes,command):
 client.images.pull(HELPER_IMAGE)
 out=client.containers.run(HELPER_IMAGE,['sh','-c',command],volumes=volumes,remove=True,stdout=True,stderr=True)
 return out.decode(errors='replace') if isinstance(out,(bytes,bytearray)) else ''
"""
new="""def run_helper(volumes,command,volumes_from=None):
 client.images.pull(HELPER_IMAGE)
 kwargs={'volumes':volumes,'remove':True,'stdout':True,'stderr':True}
 if volumes_from:kwargs['volumes_from']=volumes_from
 out=client.containers.run(HELPER_IMAGE,['sh','-c',command],**kwargs)
 return out.decode(errors='replace') if isinstance(out,(bytes,bytearray)) else ''
"""
if old not in source:raise SystemExit('1.7.2: run_helper pattern not found')
source=source.replace(old,new,1)

old="""     mounts_for_helper=_backup_mount_spec(m,'/source','ro')
     mounts_for_helper.update({str(host_backup_root()):{'bind':'/backup','mode':'rw'}})
     result=run_helper(mounts_for_helper,
      f\"if [ -d /source ]; then tar -C /source -czf /backup/{target_rel}/{archive} . && printf directory; \"
      f\"elif [ -f /source ]; then tar -C / -czf /backup/{target_rel}/{archive} source && printf file; \"
      f\"else printf special; fi\").strip()
"""
new="""     # Inherit the target container's real mounts. Do not re-bind the host
     # Source path: on NAS platforms Docker's host path may not be safely
     # re-addressable from a second helper container.
     qdest=__import__('shlex').quote(destination)
     helper_volumes={str(host_backup_root()):{'bind':'/backup','mode':'rw'}}
     result=run_helper(helper_volumes,
      f\"if [ -d {qdest} ]; then tar -C {qdest} -czf /backup/{target_rel}/{archive} . && printf directory; \"
      f\"elif [ -f {qdest} ]; then parent=$(dirname {qdest}); base=$(basename {qdest}); tar -C \\\"$parent\\\" -czf /backup/{target_rel}/{archive} \\\"$base\\\" && printf file; \"
      f\"else printf special; fi\",volumes_from=[c.id+':ro']).strip()
"""
if old not in source:raise SystemExit('1.7.2: backup helper pattern not found')
source=source.replace(old,new,1)

old="""    current_source=current.get('source'); current_type=(current.get('type') or '').lower(); current_name=current.get('name')
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
new="""    current_source=current.get('source'); current_type=(current.get('type') or '').lower(); current_name=current.get('name')
    if current_type not in ('bind','volume'):raise RuntimeError(f\"Restore target '{destination}' uses unsupported mount type '{current_type or 'unknown'}'.\")
    qdest=__import__('shlex').quote(destination)
    check=f'set -eu; test -f {qdest}; test -w {qdest}' if archive_type=='file' else f'set -eu; test -d {qdest}; test -w {qdest}'
    restore_step(f\"Preflight {index}/{len(restorable)}: type={current_type}, source={current_source or '-'}, name={current_name or '-'} -> {destination}; archive={archive}.\")
    try:run_helper({},check,volumes_from=[c.id+':rw'])
    except Exception as exc:raise RuntimeError(f\"Preflight failed for '{destination}' through target container mounts: {exc}\") from exc
    prepared.append((index,m,current_type,current_source,current_name));restore_step(f\"Preflight passed for '{destination}'.\")
"""
if old not in source:raise SystemExit('1.7.2: restore preflight pattern not found')
source=source.replace(old,new,1)

old="""    for index,m,restore_mount_key,current_type,current_source,current_name in prepared:
     destination=m.get('destination');archive=m.get('archive');archive_type=m.get('archive_type','directory')
     restore_step(f\"Restoring {index}/{len(prepared)}: type={current_type}, source={current_source or '-'}, name={current_name or '-'} -> {destination} from {archive}.\")
     command=f\"set -eu; tar -xOzf /backup/{rel}/{archive} source > /target\" if archive_type=='file' else f\"set -eu; mkdir -p /target; find /target -mindepth 1 -maxdepth 1 -exec rm -rf -- {{}} +; tar -C /target -xzf /backup/{rel}/{archive}\"
     try:run_helper({restore_mount_key:{'bind':'/target','mode':'rw'},str(host_backup_root()):{'bind':'/backup','mode':'ro'}},command)
     except Exception as exc:raise RuntimeError(f\"Restore failed for '{destination}' ({current_type}, {restore_mount_key}) from '{archive}': {exc}\") from exc
     restored.append(destination);restore_step(f\"Restored '{destination}' successfully.\")
"""
new="""    for index,m,current_type,current_source,current_name in prepared:
     destination=m.get('destination');archive=m.get('archive');archive_type=m.get('archive_type','directory');qdest=__import__('shlex').quote(destination)
     restore_step(f\"Restoring {index}/{len(prepared)}: type={current_type}, source={current_source or '-'}, name={current_name or '-'} -> {destination} from {archive}.\")
     if archive_type=='file':
      parent=__import__('shlex').quote(str(Path(destination).parent));base=__import__('shlex').quote(Path(destination).name)
      command=f\"set -eu; tar -xOzf /backup/{rel}/{archive} {base} > {qdest}\"
     else:
      command=f\"set -eu; find {qdest} -mindepth 1 -maxdepth 1 -exec rm -rf -- {{}} +; tar -C {qdest} -xzf /backup/{rel}/{archive}\"
     try:run_helper({str(host_backup_root()):{'bind':'/backup','mode':'ro'}},command,volumes_from=[c.id+':rw'])
     except Exception as exc:raise RuntimeError(f\"Restore failed for '{destination}' through target container mounts from '{archive}': {exc}\") from exc
     restored.append(destination);restore_step(f\"Restored '{destination}' successfully.\")
"""
if old not in source:raise SystemExit('1.7.2: restore loop pattern not found')
source=source.replace(old,new,1)

path.write_text(source,encoding='utf-8')
