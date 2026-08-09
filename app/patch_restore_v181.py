from pathlib import Path

path=Path('/app/main.py')
source=path.read_text(encoding='utf-8')

old="client=docker.from_env(); app=FastAPI(title=APP_NAME,version=VERSION)"
new="DOCKER_TIMEOUT=max(30,int(os.getenv('DOCKER_TIMEOUT','300'))); client=docker.from_env(timeout=DOCKER_TIMEOUT); app=FastAPI(title=APP_NAME,version=VERSION)"
if old not in source:
 raise SystemExit('1.8.1: docker client initialization pattern not found')
source=source.replace(old,new,1)

old=""" restore_step(f\"Creating container '{target_name}' from image '{image}'.\")
 try:c=client.containers.create(**kwargs)
 except Exception as exc:raise RuntimeError(f\"Container '{target_name}' could not be created: {exc}\") from exc

 networks=(inspect.get('NetworkSettings') or {}).get('Networks') or {}
"""
new=""" restore_step(f\"Creating container '{target_name}' from image '{image}' (Docker timeout: {DOCKER_TIMEOUT}s).\")
 try:
  c=client.containers.create(**kwargs)
 except Exception as exc:
  # A Docker create request can time out client-side while dockerd is still
  # completing the operation. Never issue a blind second create: first look
  # for the requested container name for up to 120 seconds.
  timeout_like=isinstance(exc,(__import__('requests').exceptions.ReadTimeout,__import__('requests').exceptions.ConnectionError)) or 'read timed out' in str(exc).lower()
  if not timeout_like:
   raise RuntimeError(f\"Container '{target_name}' could not be created: {exc}\") from exc
  restore_step(f\"Docker did not answer the create request in time ({exc}). Checking whether '{target_name}' was created asynchronously.\",'warning')
  c=None
  import time
  deadline=time.monotonic()+120
  last_probe_error=None
  while time.monotonic()<deadline:
   try:
    c=client.containers.get(target_name)
    restore_step(f\"Container '{target_name}' appeared after the Docker API timeout; continuing restore with container {c.short_id}.\",'warning')
    break
   except Exception as probe_error:
    last_probe_error=probe_error
    time.sleep(2)
  if c is None:
   raise RuntimeError(f\"Container '{target_name}' create request timed out and no container appeared within 120 seconds. Original error: {exc}. Last lookup error: {last_probe_error}\") from exc

 networks=(inspect.get('NetworkSettings') or {}).get('Networks') or {}
"""
if old not in source:
 raise SystemExit('1.8.1: container create pattern not found')
source=source.replace(old,new,1)

path.write_text(source,encoding='utf-8')
