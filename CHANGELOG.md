# Changelog

All notable user-visible changes are recorded here. Changes under **Unreleased** are on `main` but are not part of the latest published tag yet.

## Unreleased

## 1.8.1 - 2026-08-09
- Increased the Docker API client timeout from the SDK default of 60 seconds to 300 seconds by default; it can be overridden with `DOCKER_TIMEOUT`.
- Made container recreation timeout-safe: if Docker does not answer the create request in time, ContBak does not blindly create a second container.
- After a timeout-like create error, ContBak checks for up to 120 seconds whether Docker completed creation asynchronously and continues the restore with that container when found.
- Kept the full Docker Archive API backup/recreate/restore round-trip CI green after the timeout handling change.

## 1.8.0 - 2026-08-09
- Replaced the helper-container/host-remount backup engine for persistent data with Docker's native container archive API.
- Bind mounts and named volumes are now backed up from the exact filesystem view of the target container using `get_archive`, eliminating Synology/DSM host-path remount assumptions.
- Persistent data is restored directly into the target container mount namespace using `put_archive` instead of mounting Docker host paths into a helper container.
- Backup archives remain compressed `.tar.gz` files and record `docker-archive-api` as their data engine in the manifest.
- New backups remain compatible with container recreation from `container-inspect.json`.
- Legacy directory backups can still be restored by the new Docker archive engine; legacy regular-file archives require a new backup because their historic archive layout cannot be mapped safely without guessing.
- Fixed asynchronous job logging so the summary is shown once and per-mount diagnostic lines remain available separately in the live job log.
- CI now performs a full persistent-data round trip: backup a real bind mount and named volume, remove the source container/data, recreate the container, restore both archives, and compare the restored file contents.

## 1.7.2 - 2026-08-09
- Changed backup run status semantics: `success` now requires a complete backup with no skipped, excluded, or failed components and with container configuration included.
- Runs with skipped/excluded components or intentionally omitted container configuration are reported as `warning`; any mount backup failure is reported as `error`.
- Backup progress now reaches 100% only when the backup operation has actually completed.
- Fixed asynchronous backup jobs so they preserve the real `success`, `warning`, or `error` result instead of overwriting normal returns as successful.
- Added terminal `warning` handling in the WebUI so warning jobs no longer remain stuck in polling.
- Changed persistent bind/volume handling so inaccessible supported persistent mounts are reported as `FAILED`, never silently downgraded to `SKIPPED`.
- Added detailed mount-access diagnostics with inherited target-container mount access plus a direct Docker mount fallback, including the reason when both methods fail.
- Added helper support for inheriting the target container's existing mounts, improving compatibility with NAS/Synology bind-mount layouts where Docker host paths may not be safely re-addressable from a second helper container.
- Kept `SKIPPED` for intentionally non-restorable technical mounts such as Docker sockets and pseudo filesystems only.
- Simplified release versioning: Git tags are now the single source of published versions; development builds identify themselves as `dev`.
- Removed the duplicate repository `VERSION` source to prevent README/source/release version drift.
- Expanded CI to verify full backup=`success`, intentionally selective backup=`warning`, bind-mount restore, named-volume restore, and persistent-data content after recreation.

## 1.7.1 - 2026-08-08
- Added detailed per-mount backup diagnostics showing `BACKED UP`, `EXCLUDED`, `SKIPPED`, or `FAILED` with mount type, source/name, destination, archive size, and reason.
- Added detailed restore preflight and per-mount restore diagnostics in the WebUI Logs page and `docker logs ContBak`.
- Fixed named-volume backup and restore to address Docker volumes by volume name instead of relying on Docker-internal host paths.
- Preserved bind-mount backup/restore through their actual Docker host paths.
- Added CI coverage that backs up a real bind mount and named volume, removes the original persistent data/container, recreates the container, restores both data sets, and verifies their contents.
- Improved persistent-data restore reliability on Docker/Synology-style hosts.

## 1.7.0 - 2026-08-08
- Added a Backup Options dialog before starting a backup.
- Container configuration and all supported persistent mounts are selected by default.
- Added per-mount selection so individual bind mounts or named volumes can be excluded from a backup.
- Technical/special mounts such as Docker sockets and pseudo filesystems remain automatically non-restorable and are recorded as skipped with a reason.
- Backup manifests record whether each component was backed up, excluded by the user, skipped for a technical reason, or failed.
- Added config-only restore support: a container can be recreated from saved configuration even when the backup contains no persistent mount archives.
- Added CI coverage for default-full backup, selective backup, and config-only recreation.

## 1.6.0
- Added full single-container recreation from `container-inspect.json` when the original container is missing.
- Added restore modes for automatic selection, existing-container data restore, and container recreation.
- Added conflict handling: abort, replace existing container, or recreate under a new name.
- Recreates common Docker settings including image, environment, command, entrypoint, hostname, user, working directory, labels, ports, restart policy, capabilities, security options, devices, health-related runtime configuration where supported, volumes, bind mounts, and networks.
- Pulls missing images, creates missing named volumes, prepares bind paths, and creates missing bridge networks.
- Restores data before starting a recreated container.
- Added a guided Restore dialog showing original container name, image, target container, mode, and conflict handling.
- Added detailed step logging to the WebUI Logs page and `docker logs ContBak`.
- A single-container recreation does not yet recreate an entire multi-service Compose stack.

## 1.5.3
- Added restore preflight checks and step-by-step restore logging.
- Added validation/preparation of restore target paths before data extraction.
- Improved container restart diagnostics after restore.

## 1.5.2
- Changed restore requests to return explicit JSON errors instead of generic Internal Server Error pages.
- Added exact backend restore errors to the WebUI and run log.
- Added fallback target-container resolution by recorded container name.
- Improved per-mount restore error reporting.

## 1.5.1
- Added persistent import completion messages.
- Refreshes the backup list immediately after a successful import.
- Keeps the Backups tab open after import/restore actions.
- Added restore progress/status messages and clearer restore results.

## 1.5.0
- Added automatic GitHub Release creation after a successful tagged Docker build.
- Added README badges for latest release, Docker pulls, Docker image, and MIT license.
- Added an in-application Versions & Updates page.
- Added a manual update check against published GitHub Releases.
- Added release history with links to GitHub release notes.
- Added Cards and Details views to the Containers page and remembered the selected view.
- Simplified deployment configuration with `CONTBAK_BASE_PATH`, `CONTBAK_VERSION`, and `WEB_PORT`.

## 1.4.2
- Replaced separate config and backup host variables with `CONTBAK_BASE_PATH`.
- Added configurable Docker image version and web port.

## 1.4.1
- Added English as the default UI language and a German language option.
- Download single backup sets as portable `.contbak` archives.
- Export multiple selected backups in one archive.
- Upload and import ContBak archives from the WebUI.
- Verify every imported file using SHA256 checksums.
- Handle duplicate imports by rename, skip, or replace.
- Show calculated backup size in the backup browser.

## 1.3.0
- Added asynchronous backup jobs with immediate UI feedback.
- Added per-container progress bar, status message and live job log.
- Added start, success and error toast notifications.
- Disabled the backup button while a job is active.
- Added automatic page refresh after successful completion.

## 1.2.3
- Skip host pseudo filesystems such as `/proc`, `/sys`, and `/dev`.
- Skip Docker sockets explicitly.
- A single unreadable mount no longer aborts the complete backup; it is recorded in `manifest.json` and the run is marked as a warning.

## 1.2.2
- Handle directory and regular-file mounts separately.
- Skip sockets and other special mounts such as `/var/run/docker.sock`.
- Restore regular-file mounts with streamed extraction.

## 1.2.1
- Helper containers bind the real Docker-host backup path instead of the internal `/backups` path.
- The web interface displays the running ContBak version.

## 1.0.0
- Automatic discovery of Docker containers, named volumes, and bind mounts.
- Individual and bulk backups.
- Optional container stop/start around a backup.
- Restore of stored mounts to an existing container.
- Daily schedules per container.
- Retention management.
- Responsive web dashboard and backup history.
- Health endpoint and Docker health check.
- Multi-architecture Docker Hub publishing.
