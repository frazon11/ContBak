from __future__ import annotations

import json
import logging
import re
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import docker
from docker.errors import APIError, DockerException, NotFound

from .config import BACKUP_HOST_ROOT, BACKUP_ROOT, HELPER_IMAGE, RETENTION_COUNT, STOP_CONTAINERS

log = logging.getLogger("contbak")
ProgressCallback = Callable[[int, str, str], None]


class ContBakError(RuntimeError):
    pass


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("._") or "container"


def utcstamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


@dataclass
class BackupRecord:
    backup_id: str
    container_name: str
    created_at: str
    archive: str
    metadata: str
    size: int
    status: str = "complete"

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class DockerService:
    def __init__(self) -> None:
        try:
            self.client = docker.from_env()
            self.client.ping()
        except DockerException as exc:
            raise ContBakError(f"Cannot connect to Docker: {exc}") from exc

    def get_container_name(self, container_id: str) -> str:
        try:
            return self.client.containers.get(container_id).name
        except NotFound as exc:
            raise ContBakError("Container not found.") from exc
        except APIError as exc:
            raise ContBakError(f"Docker error while reading container: {exc}") from exc

    def list_containers(self) -> list[dict[str, Any]]:
        rows = []
        for container in self.client.containers.list(all=True):
            labels = container.labels or {}
            if labels.get("contbak.exclude", "").lower() == "true":
                continue
            rows.append({
                "id": container.id,
                "short_id": container.short_id,
                "name": container.name,
                "image": ", ".join(container.image.tags) or container.image.short_id,
                "status": container.status,
            })
        return sorted(rows, key=lambda row: row["name"].lower())

    def _mounts(self, container: Any) -> list[dict[str, Any]]:
        container.reload()
        return [
            mount for mount in container.attrs.get("Mounts", [])
            if mount.get("Type") in {"bind", "volume"} and mount.get("Source")
        ]

    def _backup_dir(self, container_name: str) -> Path:
        target = BACKUP_ROOT / safe_name(container_name) / utcstamp()
        target.mkdir(parents=True, exist_ok=False)
        return target

    def _helper_volumes(self, mounts: list[dict[str, Any]], backup_dir: Path):
        relative = backup_dir.relative_to(BACKUP_ROOT)
        host_output = BACKUP_HOST_ROOT / relative

        # Docker runs on the Synology host. Therefore the bind source must be
        # CONTBAK_BACKUP_PATH, never BACKUP_ROOT (/backups inside ContBak).
        volumes: dict[str, dict[str, str]] = {
            str(host_output): {"bind": "/output", "mode": "rw"}
        }
        source_paths: list[str] = []
        for index, mount in enumerate(mounts):
            helper_path = f"/source/{index}"
            volumes[str(mount["Source"])] = {"bind": helper_path, "mode": "ro"}
            source_paths.append(helper_path)
        return volumes, source_paths

    def create_backup(self, container_id: str, progress: ProgressCallback | None = None) -> dict[str, Any]:
        def report(percent: int, stage: str, message: str) -> None:
            if progress:
                progress(percent, stage, message)

        report(5, "Preparing", "Reading container configuration.")
        try:
            container = self.client.containers.get(container_id)
        except NotFound as exc:
            raise ContBakError("Container not found.") from exc
        except APIError as exc:
            raise ContBakError(f"Docker error while reading container: {exc}") from exc

        backup_dir = self._backup_dir(container.name)
        archive = backup_dir / "data.tar.gz"
        metadata_file = backup_dir / "metadata.json"
        was_running = container.status == "running"
        stopped_by_us = False
        backup_error: Exception | None = None
        restart_error: Exception | None = None

        metadata: dict[str, Any] = {
            "format_version": 1,
            "container_id": container.id,
            "container_name": container.name,
            "image": ", ".join(container.image.tags) or container.image.short_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "archive": archive.name,
            "status": "started",
        }
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        try:
            if STOP_CONTAINERS and was_running:
                report(15, "Stopping", f"Stopping {container.name} for a consistent backup.")
                container.stop(timeout=30)
                stopped_by_us = True

            report(30, "Inspecting", "Collecting bind mounts and Docker volumes.")
            mounts = self._mounts(container)
            metadata["mounts"] = mounts
            volumes, sources = self._helper_volumes(mounts, backup_dir)

            if sources:
                source_args = " ".join(shlex.quote(path.lstrip("/")) for path in sources)
                command = f"set -eu; cd /; tar -czf /output/data.tar.gz {source_args}"
            else:
                command = "set -eu; mkdir -p /empty; tar -czf /output/data.tar.gz -C /empty ."

            report(45, "Archiving", f"Creating archive using {HELPER_IMAGE}.")
            output = self.client.containers.run(
                HELPER_IMAGE,
                ["sh", "-c", command],
                remove=True,
                volumes=volumes,
                labels={"contbak.helper": "true", "contbak.exclude": "true"},
                stdout=True,
                stderr=True,
            )
            report(80, "Finalizing", "Writing metadata and applying retention.")
            metadata["helper_output"] = output.decode("utf-8", errors="replace")[-4000:]
            metadata["status"] = "complete"
        except Exception as exc:
            backup_error = exc
            metadata["status"] = "failed"
            metadata["error"] = str(exc)
            log.exception("Backup failed for %s", container.name)
        finally:
            if stopped_by_us:
                try:
                    report(88, "Restarting", f"Restarting {container.name}.")
                    container.reload()
                    container.start()
                except Exception as exc:
                    restart_error = exc
                    metadata["restart_error"] = str(exc)
                    log.exception("Restart failed for %s", container.name)
            metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        if backup_error or restart_error:
            parts = []
            if backup_error:
                parts.append(f"Backup failed: {backup_error}")
            if restart_error:
                parts.append(f"Container restart failed: {restart_error}")
            raise ContBakError(" | ".join(parts))

        self.apply_retention(container.name)
        report(100, "Complete", f"Backup of {container.name} completed.")
        return self._record_from_dir(backup_dir).as_dict()

    def apply_retention(self, container_name: str) -> None:
        container_dir = BACKUP_ROOT / safe_name(container_name)
        if not container_dir.exists():
            return
        directories = sorted([p for p in container_dir.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True)
        for old in directories[RETENTION_COUNT:]:
            self._remove_tree(old)

    def _record_from_dir(self, directory: Path) -> BackupRecord:
        metadata_path = directory / "metadata.json"
        archive_path = directory / "data.tar.gz"
        data: dict[str, Any] = {}
        if metadata_path.exists():
            try:
                data = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
        created = data.get("created_at") or datetime.fromtimestamp(directory.stat().st_mtime, tz=timezone.utc).isoformat()
        return BackupRecord(
            backup_id=directory.relative_to(BACKUP_ROOT).as_posix(),
            container_name=data.get("container_name") or directory.parent.name,
            created_at=created,
            archive=archive_path.relative_to(BACKUP_ROOT).as_posix() if archive_path.exists() else "",
            metadata=metadata_path.relative_to(BACKUP_ROOT).as_posix() if metadata_path.exists() else "",
            size=archive_path.stat().st_size if archive_path.exists() else 0,
            status=data.get("status", "unknown"),
        )

    def list_backups(self) -> list[dict[str, Any]]:
        records: list[BackupRecord] = []
        known_dirs: set[Path] = set()
        for metadata_path in BACKUP_ROOT.rglob("metadata.json"):
            directory = metadata_path.parent
            records.append(self._record_from_dir(directory))
            known_dirs.add(directory)
        for archive in BACKUP_ROOT.rglob("*.tar.gz"):
            if archive.parent in known_dirs:
                continue
            records.append(BackupRecord(
                backup_id=archive.parent.relative_to(BACKUP_ROOT).as_posix(),
                container_name=archive.parent.parent.name or "legacy",
                created_at=datetime.fromtimestamp(archive.stat().st_mtime, tz=timezone.utc).isoformat(),
                archive=archive.relative_to(BACKUP_ROOT).as_posix(),
                metadata="",
                size=archive.stat().st_size,
                status="legacy",
            ))
        return [r.as_dict() for r in sorted(records, key=lambda item: item.created_at, reverse=True)]

    def _remove_tree(self, target: Path) -> None:
        for child in sorted(target.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink(missing_ok=True)
            elif child.is_dir():
                child.rmdir()
        target.rmdir()

    def delete_backup(self, backup_id: str) -> None:
        root = BACKUP_ROOT.resolve()
        target = (BACKUP_ROOT / backup_id).resolve()
        if target == root or root not in target.parents:
            raise ContBakError("Invalid backup path.")
        if not target.exists():
            raise ContBakError("Backup not found.")
        if target.is_file():
            target.unlink()
        else:
            self._remove_tree(target)
