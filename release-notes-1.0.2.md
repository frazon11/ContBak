# ContBak 1.0.2

This release fixes the Docker-outside-of-Docker host-path error that caused
helper containers to request `/backups` from the Synology host.

The helper now uses the real host path configured through
`CONTBAK_BACKUP_PATH`.
