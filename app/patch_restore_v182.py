from pathlib import Path

path=Path('/app/main.py')
source=path.read_text(encoding='utf-8')

old=""" restore_step(f\"Creating container '{target_name}' from image '{image}' (Docker timeout: {DOCKER_TIMEOUT}s).\")
 try:
  c=client.containers.create(**kwargs)
"""
new=""" # Enforce the configured timeout on the live low-level API client as well.
 # This protects against stale/default client state and makes the effective
 # value deterministic immediately before the potentially slow create call.
 client.api.timeout=DOCKER_TIMEOUT
 effective_timeout=getattr(client.api,'timeout',None)
 restore_step(f\"Creating container '{target_name}' from image '{image}' (Docker timeout configured={DOCKER_TIMEOUT}s, effective={effective_timeout}s).\")
 try:
  c=client.containers.create(**kwargs)
"""
if old not in source:
 raise SystemExit('1.8.2: timeout enforcement create pattern not found')
source=source.replace(old,new,1)

old="@app.get('/health')\ndef health(): return {'status':'ok','name':APP_NAME,'version':VERSION}"
new="@app.get('/health')\ndef health(): return {'status':'ok','name':APP_NAME,'version':VERSION,'docker_timeout_configured':DOCKER_TIMEOUT,'docker_timeout_effective':getattr(client.api,'timeout',None)}"
if old not in source:
 raise SystemExit('1.8.2: health endpoint pattern not found')
source=source.replace(old,new,1)

path.write_text(source,encoding='utf-8')
