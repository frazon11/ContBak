# Changelog

All notable user-visible changes are recorded here. Changes under **Unreleased** are on `main` but are not part of the latest published tag yet.

## Unreleased
- Changed backup run status semantics: `success` now requires a complete backup with no skipped, excluded, or failed components and with container configuration included.
- Runs with skipped/excluded components or intentionally omitted container configuration are reported as `warning`.
- Any mount backup failure is reported as `error`.
- Backup progress now reaches 100% only when the backup operation has actually completed.
- Simplified release versioning: Git tags are now the single source of published versions; development builds identify themselves as `dev`.
- Removed the duplicate repository `VERSION` source to prevent README/source/release version drift.

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
