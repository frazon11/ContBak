from __future__ import annotations
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import APP_VERSION, BACKUP_ROOT
from .docker_service import ContBakError, DockerService
from .models import BackupRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="ContBak", version=APP_VERSION)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

def service() -> DockerService:
    return DockerService()

@app.exception_handler(ContBakError)
async def handle_contbak_error(_, exc: ContBakError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.get("/")
def index():
    return FileResponse(static_dir / "index.html")

@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION}

@app.get("/api/info")
def info():
    return {"version": APP_VERSION, "backup_root": str(BACKUP_ROOT)}

@app.get("/api/containers")
def containers():
    return service().list_containers()

@app.get("/api/backups")
def backups():
    return service().list_backups()

@app.post("/api/backups")
def create_backup(request: BackupRequest):
    return service().create_backup(request.container_id)

@app.delete("/api/backups/{backup_id:path}")
def delete_backup(backup_id: str):
    service().delete_backup(backup_id)
    return {"ok": True}
