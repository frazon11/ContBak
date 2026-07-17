from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    id: str
    container_id: str
    container_name: str
    status: str = "queued"
    progress: int = 0
    stage: str = "Queued"
    message: str = "Backup queued."
    error: str | None = None
    result: dict[str, Any] | None = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._container_jobs: dict[str, str] = {}

    def create(self, container_id: str, container_name: str) -> Job:
        with self._lock:
            existing_id = self._container_jobs.get(container_id)
            if existing_id:
                existing = self._jobs.get(existing_id)
                if existing and existing.status in {"queued", "running"}:
                    return existing
            job = Job(id=uuid.uuid4().hex, container_id=container_id, container_name=container_name)
            self._jobs[job.id] = job
            self._container_jobs[container_id] = job.id
            return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **changes: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)
            job.updated_at = now_iso()
            if job.status in {"complete", "failed"}:
                self._container_jobs.pop(job.container_id, None)

    def start(self, job: Job, worker: Callable[[str], None]) -> None:
        thread = threading.Thread(target=worker, args=(job.id,), daemon=True, name=f"contbak-{job.id[:8]}")
        thread.start()


jobs = JobManager()
