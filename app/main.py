import base64, json, os, re, secrets, sqlite3, threading
from datetime import datetime
from pathlib import Path
from typing import Optional
import docker
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

APP_NAME='ContBak'; VERSION='1.0.0'
BACKUP_ROOT=Path(os.getenv('BACKUP_ROOT','/backups')); DATA_ROOT=Path('/data')
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

def run_helper(volumes,command):
 client.images.pull(HELPER_IMAGE)
 out=client.containers.run(HELPER_IMAGE,['sh','-c',command],volumes=volumes,remove=True,stdout=True,stderr=True)
 return out.decode(errors='replace')

def add_run(name,started,status,message,path=''):
 with db_conn() as c:c.execute('INSERT INTO runs(container_name,started,ended,status,message,path) VALUES(?,?,?,?,?,?)',(name,started,datetime.now().isoformat(timespec='seconds'),status,message,path))

def prune(folder):
 if not folder.exists(): return
 sets=sorted([p for p in folder.iterdir() if p.is_dir()],reverse=True)
 import shutil
 for old in sets[RETENTION_COUNT:]: shutil.rmtree(old,ignore_errors=True)

def backup_container(container_id,stop:Optional[bool]=None):
 with lock:
  started=datetime.now().isoformat(timespec='seconds'); c=client.containers.get(container_id); info=container_info(c)
  was_running=c.status=='running'; should_stop=STOP_DEFAULT if stop is None else stop
  stamp=datetime.now().strftime('%Y-%m-%d_%H-%M-%S'); target_rel=f'{safe(c.name)}/{stamp}'; target=BACKUP_ROOT/target_rel; target.mkdir(parents=True,exist_ok=True)
  try:
   if was_running and should_stop:c.stop(timeout=30)
   (target/'container-inspect.json').write_text(json.dumps(c.attrs,indent=2),encoding='utf-8')
   for i,m in enumerate(info['mounts']):
    archive=f"mount_{i:02d}_{safe(Path(m['destination']).name or 'root')}.tar.gz"; source=m['source']
    run_helper({source:{'bind':'/source','mode':'ro'},str(BACKUP_ROOT):{'bind':'/backup','mode':'rw'}},f'tar -C /source -czf /backup/{target_rel}/{archive} .'); m['archive']=archive
   (target/'manifest.json').write_text(json.dumps(info,indent=2),encoding='utf-8'); prune(BACKUP_ROOT/safe(c.name)); add_run(c.name,started,'success',f"{len(info['mounts'])} Mount(s) gesichert",str(target))
  except Exception as e: add_run(c.name,started,'error',str(e),str(target)); raise
  finally:
   if was_running and should_stop:
    try:c.start()
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
    rel=target.relative_to(BACKUP_ROOT); source=m['source']
    run_helper({source:{'bind':'/target','mode':'rw'},str(BACKUP_ROOT):{'bind':'/backup','mode':'ro'}},f"find /target -mindepth 1 -maxdepth 1 -exec rm -rf -- {{}} +; tar -C /target -xzf /backup/{rel}/{m['archive']}")
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
 return templates.TemplateResponse('index.html',{'request':request,'containers':containers,'runs':runs,'jobs':jobs,'backups':backups[:50],'stop_default':STOP_DEFAULT})
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
