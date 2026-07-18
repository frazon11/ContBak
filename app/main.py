import base64, json, os, re, secrets, sqlite3, threading, uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import docker
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

APP_NAME='ContBak'; VERSION='1.3.0'
BACKUP_ROOT=Path(os.getenv('BACKUP_ROOT','/backups')); HOST_BACKUP_ROOT=os.getenv('CONTBAK_BACKUP_PATH'); DATA_ROOT=Path('/data')
HELPER_IMAGE=os.getenv('HELPER_IMAGE','alpine:3.22')
STOP_DEFAULT=os.getenv('STOP_CONTAINERS','true').lower()=='true'
RETENTION_COUNT=int(os.getenv('RETENTION_COUNT','7'))
USER=os.getenv('CONTBAK_USER',os.getenv('DOCKBACK_USER','admin'))
PASSWORD=os.getenv('CONTBAK_PASSWORD',os.getenv('DOCKBACK_PASSWORD','change-this-password'))
DB=DATA_ROOT/'contbak.db'
BACKUP_ROOT.mkdir(parents=True,exist_ok=True); DATA_ROOT.mkdir(parents=True,exist_ok=True)
client=docker.from_env(); app=FastAPI(title=APP_NAME,version=VERSION)
app.mount('/static',StaticFiles(directory='static'),name='static')
templates=Jinja2Templates(directory='templates'); lock=threading.Lock()
job_lock=threading.Lock(); active_jobs={}



def update_job(job_id, **changes):
 with job_lock:
  job=active_jobs.get(job_id)
  if not job:return
  job.update(changes)
  if 'message' in changes:
   job.setdefault('log',[]).append({'time':datetime.now().strftime('%H:%M:%S'),'message':str(changes['message'])})

def job_progress(job_id,progress,message,status='running'):
 update_job(job_id,progress=max(0,min(100,int(progress))),message=message,status=status)

def run_backup_job(job_id,container_id,stop):
 try:
  backup_container(container_id,stop,lambda p,m:job_progress(job_id,p,m))
  job_progress(job_id,100,'Backup erfolgreich abgeschlossen.','success')
 except Exception as exc:
  update_job(job_id,status='error',message=str(exc),error=str(exc),progress=100)

def start_backup_job(container_id,stop):
 c=client.containers.get(container_id)
 job_id=uuid.uuid4().hex
 with job_lock:
  active_jobs[job_id]={'id':job_id,'container_id':container_id,'container_name':c.name,'status':'queued','progress':0,'message':'Backup wird vorbereitet …','error':None,'log':[{'time':datetime.now().strftime('%H:%M:%S'),'message':'Backup angefordert.'}]}
 threading.Thread(target=run_backup_job,args=(job_id,container_id,stop),daemon=True,name=f'backup-{job_id[:8]}').start()
 return active_jobs[job_id].copy()

def db_conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
 with db_conn() as c:
  c.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, container_id TEXT, container_name TEXT, schedule TEXT, enabled INTEGER DEFAULT 1)')
  c.execute('CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, container_name TEXT, started TEXT, ended TEXT, status TEXT, message TEXT, path TEXT)')

def auth(request:Request):
 h=request.headers.get('authorization','')
 if not h.startswith('Basic '): raise HTTPException(401,headers={'WWW-Authenticate':'Basic'})
 try:u,p=base64.b64decode(h[6:]).decode().split(':',1)
 except Exception: raise HTTPException(401,headers={'WWW-Authenticate':'Basic'})
 if not(secrets.compare_digest(u,USER) and secrets.compare_digest(p,PASSWORD)): raise HTTPException(401,headers={'WWW-Authenticate':'Basic'})

def safe(s): return re.sub(r'[^A-Za-z0-9_.-]+','_',s)

def container_info(c):
 c.reload(); mounts=[]
 for m in c.attrs.get('Mounts',[]): mounts.append({'type':m.get('Type'),'name':m.get('Name') or m.get('Source'),'source':m.get('Source'),'destination':m.get('Destination'),'rw':m.get('RW')})
 labels=c.labels or {}
 return {'id':c.id,'short_id':c.short_id,'name':c.name,'image':', '.join(c.image.tags) or c.image.short_id,'status':c.status,'mounts':mounts,'stack':labels.get('com.docker.compose.project',''),'service':labels.get('com.docker.compose.service','')}


def host_backup_root():
 if HOST_BACKUP_ROOT:return Path(HOST_BACKUP_ROOT)
 try:
  current=client.containers.get(os.getenv('HOSTNAME',''))
  for m in current.attrs.get('Mounts',[]):
   if m.get('Destination')==str(BACKUP_ROOT) and m.get('Source'):return Path(m['Source'])
 except Exception:pass
 raise RuntimeError('CONTBAK_BACKUP_PATH fehlt. Bitte den echten Hostpfad des /backups-Mounts setzen.')


PSEUDO_FS_ROOTS = ('/proc', '/sys', '/dev')
SPECIAL_MOUNT_SOURCES = ('/var/run/docker.sock', '/run/docker.sock')

def pseudo_or_special_mount(m):
 source=os.path.normpath(m.get('source') or '')
 destination=os.path.normpath(m.get('destination') or '')
 if source in SPECIAL_MOUNT_SOURCES:
  return 'Docker-Socket wird nicht gesichert.'
 for root in PSEUDO_FS_ROOTS:
  if source == root or source.startswith(root + os.sep):
   return f'Pseudo-Dateisystem {source} wird nicht gesichert.'
  if destination == root or destination.startswith(root + os.sep):
   return f'Pseudo-Dateisystem am Ziel {destination} wird nicht gesichert.'
 return None

def run_helper(volumes,command):
 client.images.pull(HELPER_IMAGE)
 out=client.containers.run(HELPER_IMAGE,['sh','-c',command],volumes=volumes,remove=True,stdout=True,stderr=True)
 return out.decode(errors='replace') if isinstance(out,(bytes,bytearray)) else ''

def add_run(name,started,status,message,path=''):
 with db_conn() as c:c.execute('INSERT INTO runs(container_name,started,ended,status,message,path) VALUES(?,?,?,?,?,?)',(name,started,datetime.now().isoformat(timespec='seconds'),status,message,path))

def prune(folder):
 if not folder.exists(): return
 sets=sorted([p for p in folder.iterdir() if p.is_dir()],reverse=True)
 import shutil
 for old in sets[RETENTION_COUNT:]: shutil.rmtree(old,ignore_errors=True)

def backup_container(container_id,stop:Optional[bool]=None,progress=None):
 with lock:
  started=datetime.now().isoformat(timespec='seconds'); c=client.containers.get(container_id); info=container_info(c)
  was_running=c.status=='running'; should_stop=STOP_DEFAULT if stop is None else stop
  if progress:progress(3,f'Container {c.name} wird vorbereitet …')
  stamp=datetime.now().strftime('%Y-%m-%d_%H-%M-%S'); target_rel=f'{safe(c.name)}/{stamp}'; target=BACKUP_ROOT/target_rel; target.mkdir(parents=True,exist_ok=True)
  try:
   if was_running and should_stop:
    if progress:progress(8,'Container wird gestoppt …')
    c.stop(timeout=30)
   if progress:progress(12,'Container-Metadaten werden gespeichert …')
   (target/'container-inspect.json').write_text(json.dumps(c.attrs,indent=2),encoding='utf-8')
   backed_up=0; skipped=0; failed=0
   mounts=info['mounts']; total=max(1,len(mounts))
   for i,m in enumerate(mounts):
    if progress:progress(15 + int((i/total)*70),f"Mount {i+1}/{len(mounts)} wird geprüft: {m.get('destination','')}")
    archive=f"mount_{i:02d}_{safe(Path(m['destination']).name or 'root')}.tar.gz"; source=m['source']
    skip_reason=pseudo_or_special_mount(m)
    if skip_reason:
     m['archive']=None;m['archive_type']='skipped';m['skipped_reason']=skip_reason;skipped+=1;continue
    try:
     result=run_helper(
      {source:{'bind':'/source','mode':'ro'},str(host_backup_root()):{'bind':'/backup','mode':'rw'}},
      f"if [ -d /source ]; then tar -C /source -czf /backup/{target_rel}/{archive} . && printf directory; "
      f"elif [ -f /source ]; then tar -C / -czf /backup/{target_rel}/{archive} source && printf file; "
      f"else printf special; fi"
     ).strip()
     if result=='directory':m['archive']=archive;m['archive_type']='directory';backed_up+=1
     elif result=='file':m['archive']=archive;m['archive_type']='file';backed_up+=1
     else:m['archive']=None;m['archive_type']='special';m['skipped_reason']='Mount ist weder Verzeichnis noch reguläre Datei.';skipped+=1
    except Exception as mount_error:
     m['archive']=None;m['archive_type']='error';m['skipped_reason']=str(mount_error);failed+=1
   if progress:progress(88,'Manifest wird gespeichert …')
   (target/'manifest.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
   if progress:progress(93,'Alte Backups werden bereinigt …')
   prune(BACKUP_ROOT/safe(c.name))
   status='success' if failed==0 else 'warning'
   add_run(c.name,started,status,f"{backed_up} gesichert, {skipped} übersprungen, {failed} fehlgeschlagen",str(target))
   if progress:progress(97,f'{backed_up} gesichert, {skipped} übersprungen, {failed} fehlgeschlagen')
  except Exception as e: add_run(c.name,started,'error',str(e),str(target)); raise
  finally:
   if was_running and should_stop:
    try:
     if progress:progress(99,'Container wird wieder gestartet …')
     c.start()
    except Exception:pass

def restore_backup(rel_path):
 with lock:
  target=(BACKUP_ROOT/rel_path).resolve()
  if BACKUP_ROOT.resolve() not in target.parents or not target.exists(): raise ValueError('Ungültiger Backup-Pfad')
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

def scheduled_backup(cid):
 try:backup_container(cid)
 except Exception:pass

def load_jobs():
 scheduler.remove_all_jobs()
 with db_conn() as c:
  for j in c.execute('SELECT * FROM jobs WHERE enabled=1'):
   hour,minute=map(int,j['schedule'].split(':')); scheduler.add_job(scheduled_backup,'cron',hour=hour,minute=minute,args=[j['container_id']],id=f"job-{j['id']}",replace_existing=True)

init_db(); scheduler=BackgroundScheduler(timezone=os.getenv('TZ','Europe/Brussels')); scheduler.start(); load_jobs()
@app.get('/health')
def health(): return {'status':'ok','name':APP_NAME,'version':VERSION}
@app.get('/',response_class=HTMLResponse)
def home(request:Request):
 auth(request); containers=[container_info(c) for c in client.containers.list(all=True) if not (c.labels or {}).get('contbak.exclude') == 'true' and c.name != 'ContBak']
 with db_conn() as db:runs=db.execute('SELECT * FROM runs ORDER BY id DESC LIMIT 15').fetchall(); jobs=db.execute('SELECT * FROM jobs ORDER BY container_name').fetchall()
 backups=[]
 for mf in BACKUP_ROOT.glob('*/*/manifest.json'):
  try:
   data=json.loads(mf.read_text()); backups.append({'container':data['name'],'path':str(mf.parent.relative_to(BACKUP_ROOT)),'date':mf.parent.name,'mounts':len(data.get('mounts',[]))})
  except Exception:pass
 backups.sort(key=lambda x:x['date'],reverse=True)
 return templates.TemplateResponse('index.html',{'request':request,'containers':containers,'runs':runs,'jobs':jobs,'backups':backups[:50],'stop_default':STOP_DEFAULT,'version':VERSION})
@app.post('/api/backup/{container_id}')
def api_backup_one(request:Request,container_id:str,stop:Optional[str]=Form(None)):
 auth(request)
 try:return JSONResponse(start_backup_job(container_id,stop=='on'),status_code=202)
 except Exception as exc:return JSONResponse({'error':str(exc)},status_code=400)

@app.get('/api/jobs/{job_id}')
def api_job(request:Request,job_id:str):
 auth(request)
 with job_lock:job=active_jobs.get(job_id)
 if not job:raise HTTPException(404,'Job nicht gefunden')
 return job.copy()

@app.post('/backup/{container_id}')
def backup_one(request:Request,container_id:str,stop:Optional[str]=Form(None)): auth(request); backup_container(container_id,stop=='on'); return RedirectResponse('/',303)
@app.post('/backup-all')
def backup_all(request:Request):
 auth(request)
 for c in client.containers.list(all=True):
  if not (c.labels or {}).get('contbak.exclude') == 'true' and c.name != 'ContBak':
   try:backup_container(c.id)
   except Exception:pass
 return RedirectResponse('/',303)
@app.post('/restore')
def restore(request:Request,path:str=Form(...)): auth(request); restore_backup(path); return RedirectResponse('/',303)
@app.post('/schedule/{container_id}')
def schedule(request:Request,container_id:str,time:str=Form(...)):
 auth(request)
 if not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',time):raise HTTPException(400,'Zeitformat HH:MM')
 c=client.containers.get(container_id)
 with db_conn() as db:db.execute('DELETE FROM jobs WHERE container_id=?',(container_id,));db.execute('INSERT INTO jobs(container_id,container_name,schedule,enabled) VALUES(?,?,?,1)',(container_id,c.name,time))
 load_jobs(); return RedirectResponse('/',303)
@app.post('/schedule-delete/{job_id}')
def schedule_delete(request:Request,job_id:int):
 auth(request)
 with db_conn() as db:db.execute('DELETE FROM jobs WHERE id=?',(job_id,))
 load_jobs(); return RedirectResponse('/',303)
