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

BACKUP_ROOT=Path(os.getenv('BACKUP_ROOT','/backups')); BACKUP_HOST_PATH=os.getenv('BACKUP_HOST_PATH','/volume1/docker/dockback/backups'); DATA_ROOT=Path('/data')
HELPER_IMAGE=os.getenv('HELPER_IMAGE','alpine:3.22'); STOP_DEFAULT=os.getenv('STOP_CONTAINERS','true').lower()=='true'
RETENTION_COUNT=int(os.getenv('RETENTION_COUNT','7')); USER=os.getenv('DOCKBACK_USER','admin'); PASSWORD=os.getenv('DOCKBACK_PASSWORD','change-me-now')
DB=DATA_ROOT/'dockback.db'; BACKUP_ROOT.mkdir(parents=True,exist_ok=True); DATA_ROOT.mkdir(parents=True,exist_ok=True)
client=docker.from_env(); app=FastAPI(title='DockBack'); templates=Jinja2Templates(directory='templates'); app.mount('/static',StaticFiles(directory='static'),name='static'); lock=threading.Lock()

def db_conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
 with db_conn() as c:
  c.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, container_id TEXT, container_name TEXT, schedule TEXT, enabled INTEGER DEFAULT 1)')
  c.execute('CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, container_name TEXT, started TEXT, ended TEXT, status TEXT, message TEXT, path TEXT)')

def auth(r):
 h=r.headers.get('authorization','')
 if not h.startswith('Basic '): raise HTTPException(401,headers={'WWW-Authenticate':'Basic'})
 try: u,p=base64.b64decode(h[6:]).decode().split(':',1)
 except Exception: raise HTTPException(401,headers={'WWW-Authenticate':'Basic'})
 if not(secrets.compare_digest(u,USER) and secrets.compare_digest(p,PASSWORD)): raise HTTPException(401,headers={'WWW-Authenticate':'Basic'})

def safe(s): return re.sub(r'[^A-Za-z0-9_.-]+','_',s)

def container_info(c):
 c.reload(); mounts=[]
 for i,m in enumerate(c.attrs.get('Mounts',[])):
  mounts.append({'key':str(i),'type':m.get('Type'),'source':m.get('Source'),'destination':m.get('Destination'),'rw':m.get('RW')})
 labels=c.labels or {}
 return {'id':c.id,'name':c.name,'image':', '.join(c.image.tags) or c.image.short_id,'status':c.status,'mounts':mounts,'stack':labels.get('com.docker.compose.project','')}

def helper(volumes,cmd):
 client.images.pull(HELPER_IMAGE)
 return client.containers.run(HELPER_IMAGE,['sh','-c',cmd],volumes=volumes,remove=True,stdout=True,stderr=True)

def add_run(name,started,status,message,path=''):
 with db_conn() as c: c.execute('INSERT INTO runs(container_name,started,ended,status,message,path) VALUES(?,?,?,?,?,?)',(name,started,datetime.now().isoformat(timespec='seconds'),status,message,path))

def prune(d):
 import shutil
 for old in sorted([p for p in d.iterdir() if p.is_dir()],reverse=True)[RETENTION_COUNT:]: shutil.rmtree(old,ignore_errors=True)

def backup_container(cid,stop=None,selected_mounts=None):
 with lock:
  started=datetime.now().isoformat(timespec='seconds'); c=client.containers.get(cid); info=container_info(c); allm=info['mounts']
  mounts=allm if selected_mounts is None else [m for m in allm if m['key'] in set(selected_mounts)]
  if not mounts: raise ValueError('Keine Daten ausgewählt')
  was_running=c.status=='running'; should_stop=STOP_DEFAULT if stop is None else stop; stamp=datetime.now().strftime('%Y-%m-%d_%H-%M-%S'); rel=f"{safe(c.name)}/{stamp}"; target=BACKUP_ROOT/rel; target.mkdir(parents=True,exist_ok=True)
  try:
   if was_running and should_stop: c.stop(timeout=30)
   (target/'container-inspect.json').write_text(json.dumps(c.attrs,indent=2),encoding='utf-8')
   manifest=dict(info); manifest['mounts']=mounts; manifest['all_mounts_count']=len(allm); manifest['backup_mode']='all' if len(mounts)==len(allm) else 'selected'; manifest['status']='running'; manifest['created_at']=started
   for m in mounts:
    archive=f"mount_{int(m['key']):02d}_{safe(Path(m['destination']).name or 'root')}.tar.gz"; m['archive']=archive
   # Manifest zuerst schreiben, damit auch abgebrochene Backups sichtbar bleiben.
   (target/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
   for m in mounts:
    helper({m['source']:{'bind':'/source','mode':'ro'},BACKUP_HOST_PATH:{'bind':'/backup','mode':'rw'}},f"tar -C /source -czf /backup/{rel}/{m['archive']} .")
   manifest['status']='complete'; manifest['completed_at']=datetime.now().isoformat(timespec='seconds')
   (target/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8'); prune(BACKUP_ROOT/safe(c.name)); add_run(c.name,started,'success',f"{len(mounts)} von {len(allm)} Mount(s) gesichert",str(target))
  except Exception as e: add_run(c.name,started,'error',str(e),str(target)); raise
  finally:
   if was_running and should_stop:
    try: c.start()
    except Exception: pass

def restore_backup(rel,archives=None):
 with lock:
  target=(BACKUP_ROOT/rel).resolve()
  if BACKUP_ROOT.resolve() not in target.parents: raise ValueError('Ungültiger Pfad')
  manifest=json.loads((target/'manifest.json').read_text()); c=client.containers.get(manifest['id']); mounts=manifest['mounts']
  if archives: mounts=[m for m in mounts if m.get('archive') in set(archives)]
  if not mounts: raise ValueError('Keine Daten ausgewählt')
  was_running=c.status=='running'
  if was_running: c.stop(timeout=30)
  try:
   for m in mounts:
    helper({m['source']:{'bind':'/target','mode':'rw'},BACKUP_HOST_PATH:{'bind':'/backup','mode':'ro'}},f"find /target -mindepth 1 -maxdepth 1 -exec rm -rf -- {{}} +; tar -C /target -xzf /backup/{target.relative_to(BACKUP_ROOT)}/{m['archive']}")
  finally: c.start()

def scheduled(cid):
 try: backup_container(cid)
 except Exception: pass

def load_jobs():
 scheduler.remove_all_jobs()
 with db_conn() as c:
  for j in c.execute('SELECT * FROM jobs WHERE enabled=1'):
   h,m=map(int,j['schedule'].split(':')); scheduler.add_job(scheduled,'cron',hour=h,minute=m,args=[j['container_id']],id=f"job-{j['id']}",replace_existing=True)

init_db(); scheduler=BackgroundScheduler(timezone=os.getenv('TZ','Europe/Berlin')); scheduler.start(); load_jobs()

@app.get('/',response_class=HTMLResponse)
def home(request:Request):
 auth(request); containers=[container_info(c) for c in client.containers.list(all=True) if c.name!='DockBack']; backups=[]; seen=set()
 # Rekursiv suchen: unterstützt auch importierte oder anders verschachtelte Backup-Ordner.
 for mf in BACKUP_ROOT.rglob('manifest.json'):
  try:
   d=json.loads(mf.read_text()); rel=str(mf.parent.relative_to(BACKUP_ROOT)); seen.add(mf.parent.resolve())
   mounts=d.get('mounts',[])
   # Nur tatsächlich vorhandene Archive als wiederherstellbar markieren.
   for m in mounts: m['available']=(mf.parent/m.get('archive','')).is_file()
   backups.append({'container':d.get('name',mf.parent.parent.name),'path':rel,'date':mf.parent.name,'mounts':mounts,'all_mounts_count':d.get('all_mounts_count',len(mounts)),'mode':d.get('backup_mode','all'),'status':d.get('status','complete')})
  except Exception: pass
 # Alte/abgebrochene Backups ohne Manifest trotzdem anzeigen.
 for folder in BACKUP_ROOT.rglob('*'):
  if not folder.is_dir() or folder.resolve() in seen: continue
  archives=sorted(folder.glob('mount_*.tar.gz'))
  if not archives: continue
  mounts=[{'archive':a.name,'destination':a.stem,'type':'unknown','source':'Manifest fehlt','available':True} for a in archives]
  backups.append({'container':folder.parent.name,'path':str(folder.relative_to(BACKUP_ROOT)),'date':folder.name,'mounts':mounts,'all_mounts_count':len(mounts),'mode':'legacy','status':'incomplete'})
 backups.sort(key=lambda x:x['date'],reverse=True)
 with db_conn() as c: runs=c.execute('SELECT * FROM runs ORDER BY id DESC LIMIT 15').fetchall(); jobs=c.execute('SELECT * FROM jobs ORDER BY container_name').fetchall()
 return templates.TemplateResponse('index.html',{'request':request,'containers':containers,'backups':backups[:50],'runs':runs,'jobs':jobs,'stop_default':STOP_DEFAULT})

@app.post('/backup/{cid}')
def backup_one(request:Request,cid:str,stop:Optional[str]=Form(None),mounts:list[str]=Form(default=[])):
 auth(request); backup_container(cid,stop=='on',mounts); return RedirectResponse('/',303)

@app.post('/backup-selected')
def backup_selected(request:Request,containers:list[str]=Form(default=[]),stop:Optional[str]=Form(None)):
 auth(request)
 if not containers: raise HTTPException(400,'Keine Container ausgewählt')
 for cid in containers:
  try: backup_container(cid,stop=='on')
  except Exception: pass
 return RedirectResponse('/',303)

@app.post('/backup-all')
def backup_all(request:Request):
 auth(request)
 for c in client.containers.list(all=True):
  if c.name!='DockBack':
   try: backup_container(c.id)
   except Exception: pass
 return RedirectResponse('/',303)

@app.post('/restore')
def restore(request:Request,path:str=Form(...),archives:list[str]=Form(default=[])):
 auth(request); restore_backup(path,archives or None); return RedirectResponse('/',303)

@app.post('/schedule/{cid}')
def schedule(request:Request,cid:str,time:str=Form(...)):
 auth(request)
 if not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',time): raise HTTPException(400,'Zeitformat HH:MM')
 c=client.containers.get(cid)
 with db_conn() as db: db.execute('DELETE FROM jobs WHERE container_id=?',(cid,)); db.execute('INSERT INTO jobs(container_id,container_name,schedule,enabled) VALUES(?,?,?,1)',(cid,c.name,time))
 load_jobs(); return RedirectResponse('/',303)

@app.post('/schedule-delete/{jid}')
def schedule_delete(request:Request,jid:int):
 auth(request)
 with db_conn() as db: db.execute('DELETE FROM jobs WHERE id=?',(jid,))
 load_jobs(); return RedirectResponse('/',303)
