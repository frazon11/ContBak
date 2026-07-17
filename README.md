# ContBak

ContBak is a lightweight Docker container backup manager with a web interface.

## Version 1.0.3

- Helper containers receive the real Docker-host path through `CONTBAK_BACKUP_PATH`.
- `/backups` inside ContBak is no longer incorrectly used as a host bind source.
- Target containers are restarted in a `finally` block after backup attempts.
- Docker errors are shown as readable API/UI messages instead of an unhandled HTTP 500.
- The Backups tab scans recursively and also finds legacy `*.tar.gz` archives.
- Manual GitHub workflow runs always have an SHA tag; only release tags push to Docker Hub.

## Synology / Portainer

Create:

```sh
mkdir -p /volume1/docker/contbak/config
mkdir -p /volume1/docker/contbak/backups
```

Keep this in `.env`:

```env
CONTBAK_BACKUP_PATH=/volume1/docker/contbak/backups
```

The path has two different roles:

- `BACKUP_ROOT=/backups`: path inside the ContBak container.
- `CONTBAK_BACKUP_PATH=/volume1/...`: real path visible to the Synology Docker daemon.

## Release

```sh
git add -A
git commit -m "Release ContBak 1.0.3"
git push origin main
git tag -a v1.0.3 -m "ContBak 1.0.3"
git push origin v1.0.3
```

## Backup progress

The UI shows stage-based progress: preparing, stopping, inspecting, archiving, restarting, and complete. This is not a byte-exact tar percentage.
