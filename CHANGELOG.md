# Changelog

## 1.2.2 - 2026-07-18

- Handle directory and regular-file mounts separately.
- Skip sockets and other special mounts such as `/var/run/docker.sock`.
- Restore regular-file mounts with streamed extraction.

All notable changes are documented here.

## 1.2.1 — 2026-07-18

### Fixed
- Helper containers now bind the real Docker-host backup path from `CONTBAK_BACKUP_PATH` instead of the internal `/backups` container path.
- Backup and restore therefore work on Synology/Portainer without `Bind mount failed: '/backups' does not exist`.

### Changed
- The web interface now displays the running ContBak version.

## 1.0.0 — 2026-07-16

### Added
- Automatic discovery of Docker containers, named volumes, and bind mounts.
- Backup of individual containers or all discovered containers.
- Optional container stop/start around a backup.
- Restore of stored mounts to an existing container.
- Daily schedules per container.
- Retention management.
- Responsive web dashboard and backup history.
- Health endpoint and Docker health check.
- Multi-architecture Docker Hub publishing for amd64 and arm64.
- Synology and Portainer compose example.
