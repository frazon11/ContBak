from __future__ import annotations
import os
from pathlib import Path

APP_VERSION = "1.0.2"
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data"))
BACKUP_ROOT = Path(os.getenv("BACKUP_ROOT", "/backups"))
BACKUP_HOST_ROOT = Path(
    os.getenv("CONTBAK_BACKUP_PATH", os.getenv("BACKUP_HOST_ROOT", "/backups"))
)
HELPER_IMAGE = os.getenv("HELPER_IMAGE", "alpine:3.22")
STOP_CONTAINERS = os.getenv("STOP_CONTAINERS", "true").lower() in {"1","true","yes","on"}
RETENTION_COUNT = max(1, int(os.getenv("RETENTION_COUNT", "7")))
CONTBAK_USER = os.getenv("CONTBAK_USER", "admin")
CONTBAK_PASSWORD = os.getenv("CONTBAK_PASSWORD", "change-me")

DATA_ROOT.mkdir(parents=True, exist_ok=True)
BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
