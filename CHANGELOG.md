# Changelog

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
