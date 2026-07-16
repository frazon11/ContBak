# ContBak

**Container Backup Manager with a web interface.**

ContBak discovers Docker containers and their named volumes and bind mounts. It can back up one container or all containers, restore an existing backup, run daily schedules, and retain a configurable number of versions.

- GitHub: `Frazon11/ContBak`
- Docker Hub: `frazon11/contbak`
- Current version: `1.0.0`
- License: MIT

> [!WARNING]
> ContBak mounts `/var/run/docker.sock`. This grants broad administrative control over the Docker host. Keep the interface on a trusted network or behind a VPN/authenticated reverse proxy. Do not expose it directly to the Internet.

## Features

- Automatic container discovery
- Named-volume and bind-mount backups
- Per-container and backup-all actions
- Optional stop/start for better filesystem consistency
- Restore through the web interface
- Daily schedules per container
- Configurable retention
- Backup manifests and `docker inspect` metadata
- Responsive dashboard
- `linux/amd64` and `linux/arm64` images
- Synology DSM and Portainer-friendly deployment

## Quick start

Create `.env` next to `docker-compose.yml`:

```dotenv
TZ=Europe/Brussels
CONTBAK_USER=admin
CONTBAK_PASSWORD=replace-with-a-long-random-password
HELPER_IMAGE=alpine:3.22
STOP_CONTAINERS=true
RETENTION_COUNT=7
CONTBAK_CONFIG_PATH=/volume1/docker/contbak/config
CONTBAK_BACKUP_PATH=/volume1/docker/contbak/backups
```

Start ContBak:

```bash
docker compose up -d
```

Open:

```text
http://DOCKER-HOST:8787
```

## Portainer

Create the host directories first:

```text
/volume1/docker/contbak/config
/volume1/docker/contbak/backups
```

Then deploy the supplied `docker-compose.yml` as a Portainer stack and define the environment variables in Portainer or upload the `.env` file.

## Backups

Each backup is stored below `/backups/<container>/<timestamp>/` and contains:

```text
manifest.json
container-inspect.json
mount_00_<name>.tar.gz
mount_01_<name>.tar.gz
```

When `STOP_CONTAINERS=true`, a running container is stopped before its mount data is archived and started again afterward.

## Restore behavior

Version 1.0.0 restores mount contents into the original container's currently configured mounts. The container must still exist. Restore removes the existing content of every selected mount before extracting its archive.

Always keep another tested backup before using restore in production.

## Databases

Stopping the database container makes a file-level backup safer, but application-native dumps remain the preferred method for databases requiring guaranteed transactional consistency. Native database hooks are planned for a later release.

## Excluding a container

Add this label:

```yaml
labels:
  contbak.exclude: "true"
```

ContBak excludes itself by default in the included compose file.

## Publishing a release

The repository workflow publishes tagged releases to Docker Hub. Configure these GitHub Actions secrets:

```text
DOCKERHUB_USERNAME=frazon11
DOCKERHUB_TOKEN=<Docker Hub personal access token with Read & Write>
```

Then create and push a tag:

```bash
git tag -a v1.0.0 -m "ContBak 1.0.0"
git push origin v1.0.0
```

The workflow publishes:

```text
frazon11/contbak:1.0.0
frazon11/contbak:1.0
frazon11/contbak:latest
```

## Known limitations

- Deleted containers are not recreated automatically yet.
- Backups are full TAR/Gzip archives, not incremental or deduplicated.
- Backups are not encrypted by ContBak itself.
- Jobs execute sequentially.
- Restore should be tested on non-production data first.

## License

MIT License. See `LICENSE`.
