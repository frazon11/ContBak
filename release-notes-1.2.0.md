# ContBak 1.2.0

## Changes

- Fixed the helper-container backup bind mount. `CONTBAK_BACKUP_PATH` is now used as the Docker-host path, while `/backups` remains the path inside the ContBak container.
- Fixed the same host-path handling for restore operations.
- Added the running version number to the web interface.

## Required compose setting

```yaml
environment:
  BACKUP_ROOT: /backups
  CONTBAK_BACKUP_PATH: ${CONTBAK_BACKUP_PATH}
volumes:
  - ${CONTBAK_BACKUP_PATH}:/backups
```
