# Changelog

## 1.0.3 - 2026-07-17

### Fixed
- Helper container now always uses `CONTBAK_BACKUP_PATH` as Docker host bind source.
- Prevented `Bind mount failed: '/backups' does not exist` on Synology.
- Unexpected exceptions are returned as readable JSON errors instead of an HTML Internal Server Error page.
- Backup directories use microseconds to prevent duplicate directory names.
- Target containers are restarted in a `finally` block.

### Added
- Asynchronous backup jobs.
- Job status API at `/api/jobs/{job_id}`.
- Visible stage-based progress indicator with percentage.
- Duplicate-click protection while a container backup is running.
- HTTP Basic authentication using `CONTBAK_USER` and `CONTBAK_PASSWORD`.

### Changed
- Release image is `frazon11/contbak:1.0.3`.
