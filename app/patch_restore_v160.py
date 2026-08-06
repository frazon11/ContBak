from pathlib import Path

path = Path('/app/main.py')
source = path.read_text(encoding='utf-8')

start = source.index('def restore_backup(rel_path):')
end = source.index('\ndef scheduled_backup', start)

new_code = r'''def _restore_log(container_name, started, target, message, status='running'):
 text=str(message)
 print(f'[restore] {container_name}: {text}',flush=True)
 add_run(container_name,started,status,text,str(target))


def _image_name_from_inspect(inspect):
 config=inspect.get('Config') or {}
 image=config.get('Image')
 if image:return image
 raise RuntimeError('container-inspect.json contains no usable image name.')


def _port_bindings(host_config):
 result={}
 for container_port,bindings in (host_config.get('PortBindings') or {}).items():
  if not bindings:
   result[container_port]=None
   continue
  values=[]
  for binding in bindings:
   host_ip=(binding or {}).get('HostIp') or ''
   host_port=(binding or {}).get('HostPort') or None
   if host_ip and host_port:values.append((host_ip,int(host_port)))
   elif host_port:values.append(int(host_port))
   else:values.append(None)
  result[container_port]=values[0] if len(values)==1 else values
 return result


def _device_requests(host_config):
 requests=[]
 for item in host_config.get('DeviceRequests') or []:
  try:
   requests.append(docker.types.DeviceRequest(
    driver=item.get('Driver') or '',
    count=item.get('Count',-1),
    device_ids=item.get('DeviceIDs'),
    capabilities=item.get('Capabilities'),
    options=item.get('Options')
   ))
  except Exception:pass
 return requests or None


def _prepare_recreate_mounts(manifest, target_name, restore_step):
 volumes={}
 for index,m in enumerate(manifest.get('mounts') or [],1):
  destination=m.get('destination')
  source_path=m.get('source')
  mount_type=m.get('type') or 'bind'
  if not destination or not source_path:continue
  mode='rw' if m.get('rw',True) else 'ro'
  archive_type=m.get('archive_type','directory')
  if mount_type=='volume':
   volume_name=m.get('name') or source_path
   try:client.volumes.get(volume_name)
   except Exception:
    client.volumes.create(name=volume_name,labels={'contbak.restored':'true','contbak.container':target_name})
    restore_step(f"Created missing Docker volume '{volume_name}'.")
   volumes[volume_name]={'bind':destination,'mode':mode}
  elif mount_type=='bind':
   host_path=Path(source_path)
   if archive_type=='file':
    host_path.parent.mkdir(parents=True,exist_ok=True)
    if not host_path.exists():host_path.touch()
   else:
    host_path.mkdir(parents=True,exist_ok=True)
   volumes[str(host_path)]={'bind':destination,'mode':mode}
   restore_step(f"Prepared bind path '{host_path}' for '{destination}'.")
 return volumes


def _create_container_from_backup(target, manifest, target_name, conflict, restore_step):
 inspect_file=target/'container-inspect.json'
 if not inspect_file.is_file():
  raise RuntimeError('container-inspect.json is missing; the container cannot be recreated.')
 inspect=json.loads(inspect_file.read_text(encoding='utf-8'))
 config=inspect.get('Config') or {}
 host=inspect.get('HostConfig') or {}
 image=_image_name_from_inspect(inspect)

 try:
  existing=client.containers.get(target_name)
 except Exception:
  existing=None
 if existing:
  if conflict=='abort':
   raise RuntimeError(f"A container named '{target_name}' already exists. Choose existing-container restore, replace, or another name.")
  if conflict=='replace':
   restore_step(f"Removing existing container '{target_name}'.")
   try:existing.remove(force=True)
   except Exception as exc:raise RuntimeError(f"Existing container '{target_name}' could not be removed: {exc}") from exc
  elif conflict=='rename':
   base=target_name;n=1
   while True:
    candidate=f'{base}-restored-{n}'
    try:client.containers.get(candidate);n+=1
    except Exception:target_name=candidate;break
   restore_step(f"Container name conflict resolved as '{target_name}'.")

 try:client.images.get(image);restore_step(f"Image available locally: {image}.")
 except Exception:
  restore_step(f"Pulling image '{image}'.")
  try:client.images.pull(image)
  except Exception as exc:raise RuntimeError(f"Image '{image}' could not be pulled: {exc}") from exc

 volumes=_prepare_recreate_mounts(manifest,target_name,restore_step)
 restart=host.get('RestartPolicy') or {}
 restart_policy={'Name':restart.get('Name') or 'no'}
 if restart.get('MaximumRetryCount') is not None:restart_policy['MaximumRetryCount']=restart.get('MaximumRetryCount')

 kwargs={
  'image':image,
  'name':target_name,
  'detach':True,
  'environment':config.get('Env') or None,
  'command':config.get('Cmd') or None,
  'entrypoint':config.get('Entrypoint') or None,
  'hostname':config.get('Hostname') or None,
  'user':config.get('User') or None,
  'working_dir':config.get('WorkingDir') or None,
  'labels':config.get('Labels') or None,
  'ports':_port_bindings(host) or None,
  'volumes':volumes or None,
  'restart_policy':restart_policy,
  'privileged':bool(host.get('Privileged',False)),
  'cap_add':host.get('CapAdd') or None,
  'cap_drop':host.get('CapDrop') or None,
  'security_opt':host.get('SecurityOpt') or None,
  'dns':host.get('Dns') or None,
  'dns_search':host.get('DnsSearch') or None,
  'extra_hosts':host.get('ExtraHosts') or None,
  'shm_size':host.get('ShmSize') or None,
  'read_only':bool(host.get('ReadonlyRootfs',False)),
  'device_requests':_device_requests(host),
 }
 if host.get('Devices'):
  devices=[]
  for d in host.get('Devices') or []:
   if d.get('PathOnHost') and d.get('PathInContainer'):
    devices.append(f"{d['PathOnHost']}:{d['PathInContainer']}:{d.get('CgroupPermissions') or 'rwm'}")
  if devices:kwargs['devices']=devices
 kwargs={k:v for k,v in kwargs.items() if v is not None}

 restore_step(f"Creating container '{target_name}' from image '{image}'.")
 try:c=client.containers.create(**kwargs)
 except Exception as exc:raise RuntimeError(f"Container '{target_name}' could not be created: {exc}") from exc

 networks=(inspect.get('NetworkSettings') or {}).get('Networks') or {}
 connected=[]
 for network_name,net_data in networks.items():
  if network_name in ('none','host'):continue
  try:network=client.networks.get(network_name)
  except Exception:
   try:
    network=client.networks.create(network_name,driver='bridge',labels={'contbak.restored':'true'})
    restore_step(f"Created missing network '{network_name}' using bridge driver.")
   except Exception as exc:
    restore_step(f"Network '{network_name}' could not be created and will be skipped: {exc}",'warning');continue
  try:
   network.connect(c,aliases=(net_data or {}).get('Aliases') or None)
   connected.append(network_name)
  except Exception as exc:
   restore_step(f"Could not connect '{target_name}' to network '{network_name}': {exc}",'warning')
 restore_step(f"Container '{target_name}' created in stopped state. Networks: {', '.join(connected) or 'default only'}.")
 return c,target_name


def restore_info(rel_path):
 target=backup_path(rel_path)
 manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
 inspect={}
 inspect_file=target/'container-inspect.json'
 if inspect_file.is_file():
  try:inspect=json.loads(inspect_file.read_text(encoding='utf-8'))
  except Exception:pass
 name=manifest.get('name') or manifest.get('container_name') or ''
 image=(inspect.get('Config') or {}).get('Image') or ''
 existing=[]
 for c in client.containers.list(all=True):existing.append({'id':c.id,'name':c.name,'image':', '.join(c.image.tags) or c.image.short_id,'status':c.status})
 return {'path':rel_path,'original_name':name,'image':image,'can_recreate':bool(image and inspect_file.is_file()),'containers':existing,'mounts':manifest.get('mounts') or []}


def restore_backup(rel_path,mode='auto',target_name=None,conflict='abort'):
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
    candidates=[target_name,manifest.get('id'),original_name]
    for candidate in candidates:
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
   current_mounts={m.get('Destination'):{'source':m.get('Source'),'type':m.get('Type')} for m in c.attrs.get('Mounts',[]) if m.get('Destination') and m.get('Source')}
   restorable=[m for m in manifest.get('mounts',[]) if m.get('archive')]
   if not restorable:raise RuntimeError('This backup contains no restorable mount archives.')
   restore_step(f'Preflight started for {len(restorable)} mount(s).')
   prepared=[];rel=target.relative_to(BACKUP_ROOT)
   for index,m in enumerate(restorable,1):
    destination=m.get('destination');archive=m.get('archive');archive_type=m.get('archive_type','directory')
    current=current_mounts.get(destination)
    if not current:raise RuntimeError(f"Target container has no mount at '{destination}'.")
    archive_file=target/archive
    if not archive_file.is_file():raise RuntimeError(f"Archive is missing: {archive}")
    current_source=current.get('source')
    check='set -eu; test -f /target; test -w /target' if archive_type=='file' else 'set -eu; mkdir -p /target; test -d /target; test -w /target'
    try:run_helper({current_source:{'bind':'/target','mode':'rw'}},check)
    except Exception as exc:raise RuntimeError(f"Preflight failed for '{destination}' at '{current_source}': {exc}") from exc
    prepared.append((index,m,current_source));restore_step(f"Preflight passed for '{destination}'.")

   if was_running:
    restore_step(f"Stopping container '{c.name}'.");c.stop(timeout=30)
   restored=[];restore_error=None;restart_error=None
   try:
    for index,m,current_source in prepared:
     destination=m.get('destination');archive=m.get('archive');archive_type=m.get('archive_type','directory')
     restore_step(f"Restoring '{destination}' from '{archive}'.")
     command=f"set -eu; tar -xOzf /backup/{rel}/{archive} source > /target" if archive_type=='file' else f"set -eu; mkdir -p /target; find /target -mindepth 1 -maxdepth 1 -exec rm -rf -- {{}} +; tar -C /target -xzf /backup/{rel}/{archive}"
     try:run_helper({current_source:{'bind':'/target','mode':'rw'},str(host_backup_root()):{'bind':'/backup','mode':'ro'}},command)
     except Exception as exc:raise RuntimeError(f"Restore failed for '{destination}' from '{archive}': {exc}") from exc
     restored.append(destination);restore_step(f"Restored '{destination}'.")
   except Exception as exc:restore_error=exc
   finally:
    if was_running or created:
     try:restore_step(f"Starting container '{c.name}'.");c.start();restore_step(f"Container '{c.name}' started.")
     except Exception as exc:restart_error=exc
   if restore_error and restart_error:raise RuntimeError(f'{restore_error} Additionally, container start failed: {restart_error}')
   if restore_error:raise restore_error
   if restart_error:raise RuntimeError(f"Data was restored, but container '{c.name}' could not be started: {restart_error}")
   message=f"Restore completed: container '{c.name}' is available and {len(restored)} mount(s) were restored."
   restore_step(message,'success')
   return {'container':c.name,'created':created,'restored_mounts':restored,'message':message,'steps':steps}
  except Exception as exc:
   detail=f'Restore failed: {exc}';_restore_log(log_name,started,target,detail,'error');raise
'''

source = source[:start] + new_code + source[end:]

old_endpoint = """@app.post('/restore')
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
"""
new_endpoint = """@app.get('/api/restore-info')
def api_restore_info(request:Request,path:str):
 auth(request)
 try:return JSONResponse({'status':'success',**restore_info(path)})
 except Exception as exc:return JSONResponse({'status':'error','error':str(exc) or exc.__class__.__name__},status_code=400)

@app.post('/restore')
def restore(request:Request,path:str=Form(...),mode:str=Form('auto'),target_name:Optional[str]=Form(None),conflict:str=Form('abort')):
 auth(request)
 if mode not in ('auto','existing','recreate'):return JSONResponse({'status':'error','error':'Invalid restore mode.'},status_code=400)
 if conflict not in ('abort','replace','rename'):return JSONResponse({'status':'error','error':'Invalid conflict option.'},status_code=400)
 wants_json='application/json' in request.headers.get('accept','').lower()
 try:
  result=restore_backup(path,mode,target_name,conflict)
  if wants_json:return JSONResponse({'status':'success',**result})
  return RedirectResponse('/?tab=backups&restore=success',303)
 except Exception as exc:
  detail=str(exc) or exc.__class__.__name__
  return JSONResponse({'status':'error','error':detail,'type':exc.__class__.__name__},status_code=400)
"""
if old_endpoint not in source:
 raise SystemExit('ContBak 1.5.2 restore endpoint pattern not found; refusing unsafe patch.')
source=source.replace(old_endpoint,new_endpoint,1)
path.write_text(source,encoding='utf-8')
