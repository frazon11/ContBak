from __future__ import annotations

import logging
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from .config import APP_VERSION, BACKUP_ROOT, CONTBAK_PASSWORD, CONTBAK_USER
from .docker_service import ContBakError, DockerService
from .jobs import jobs
from .models import BackupRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("contbak")
security = HTTPBasic()
app = FastAPI(title="ContBak", version=APP_VERSION)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def authenticate(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    valid_user = secrets.compare_digest(credentials.username.encode(), CONTBAK_USER.encode())
    valid_password = secrets.compare_digest(credentials.password.encode(), CONTBAK_PASSWORD.encode())
    if not (valid_user and valid_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Basic"})
    return credentials.username


def service() -> DockerService:
    return DockerService()


@app.exception_handler(ContBakError)
async def handle_contbak_error(_, exc: ContBakError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def handle_unexpected_error(_, exc: Exception):
    log.exception("Unhandled application error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": f"Unexpected server error: {exc}"})


@app.get("/")
def index(_: str = Depends(authenticate)):
    return FileResponse(static_dir / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION}


@app.get("/api/info")
def info(_: str = Depends(authenticate)):
    return {"version": APP_VERSION, "backup_root": str(BACKUP_ROOT)}


@app.get("/api/containers")
def containers(_: str = Depends(authenticate)):
    return service().list_containers()


@app.get("/api/backups")
def backups(_: str = Depends(authenticate)):
    return service().list_backups()


def run_backup_job(job_id: str) -> None:
    job = jobs.get(job_id)
    if not job:
        return
    jobs.update(job_id, status="running", progress=1, stage="Starting", message="Backup job started.")
    try:
        result = service().create_backup(
            job.container_id,
            progress=lambda percent, stage, message: jobs.update(job_id, status="running", progress=percent, stage=stage, message=message),
        )
        jobs.update(job_id, status="complete", progress=100, stage="Complete", message="Backup completed successfully.", result=result)
    except Exception as exc:
        log.exception("Backup job %s failed", job_id)
        jobs.update(job_id, status="failed", stage="Failed", message=str(exc), error=str(exc))


@app.post("/api/backups", status_code=202)
def create_backup(request: BackupRequest, _: str = Depends(authenticate)):
    svc = service()
    container_name = svc.get_container_name(request.container_id)
    job = jobs.create(request.container_id, container_name)
    if job.status == "queued":
        jobs.start(job, run_backup_job)
    return job.as_dict()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, _: str = Depends(authenticate)):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Backup job not found.")
    return job.as_dict()


@app.delete("/api/backups/{backup_id:path}")
def delete_backup(backup_id: str, _: str = Depends(authenticate)):
    service().delete_backup(backup_id)
    return {"ok": True}
