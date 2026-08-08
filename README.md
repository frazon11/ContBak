# ContBak

[![Latest release](https://img.shields.io/github/v/release/Frazon11/ContBak?display_name=tag&sort=semver)](https://github.com/Frazon11/ContBak/releases/latest)
[![Docker pulls](https://img.shields.io/docker/pulls/frazon11/contbak)](https://hub.docker.com/r/frazon11/contbak)
[![Docker image](https://img.shields.io/badge/docker-frazon11%2Fcontbak-2496ED?logo=docker&logoColor=white)](https://hub.docker.com/r/frazon11/contbak)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Container Backup Manager with a web interface.**

ContBak discovers Docker containers and their named volumes and bind mounts. It supports individual and bulk backups, selectable backup components, full single-container recreation, data restore, schedules, retention, detailed progress/logging, portable `.contbak` import/export, and English/German user interfaces.

- GitHub: `Frazon11/ContBak`
- Docker Hub: `frazon11/contbak`
- Latest published version: see the **Latest release** badge above
- License: MIT

> [!WARNING]
> ContBak mounts `/var/run/docker.sock`, which grants broad administrative control over the Docker host. Keep the interface on a trusted network or behind a VPN/authenticated reverse proxy.

## Highlights

- Automatic Docker container discovery
- Card and detailed table views for containers
- Named-volume and bind-mount backups
- Selectable backup components; all supported components selected by default
- Per-container and backup-all actions
- Optional stop/start for filesystem consistency
- Detailed per-mount backup/restore logging
- Explicit `success`, `warning`, and `error` run states
- Restore data into an existing container
- Recreate a missing single container from saved Docker metadata
- Restore conflict handling: abort, replace, or use a new name
- Image pull, volume creation, bind-path preparation, ports, environment, labels, restart policy, devices, and network reconstruction
- Daily schedules and configurable retention
- Download, multi-export, upload and import of `.contbak` archives
- SHA256 verification during import
- English and German UI
- Built-in version history and update checker
- Tag-driven GitHub Releases and Docker Hub publishing
- Multi-architecture images for `linux/amd64` and `linux/arm64`

## Quick start

Create `.env` next to `docker-compose.yml`:

```dotenv
TZ=Europe/Brussels
CONTBAK_VERSION=latest
WEB_PORT=8787
CONTBAK_BASE_PATH=/volume1/docker/contbak

CONTBAK_USER=admin
CONTBAK_PASSWORD=replace-with-a-long-random-password

HELPER_IMAGE=alpine:3.22
STOP_CONTAINERS=true
RETENTION_COUNT=7
```

Start ContBak:

```bash
docker compose up -d
```

Open:

```text
http://DOCKER-HOST:8787
```

## Storage layout

`CONTBAK_BASE_PATH` is expanded automatically:

```text
/volume1/docker/contbak/config
/volume1/docker/contbak/backups
```

Each backup is stored below `/backups/<container>/<timestamp>/` and contains `manifest.json`, optional `container-inspect.json`, and one archive per selected supported persistent mount.

## Backup status semantics

ContBak treats run states strictly:

- **success**: every selected supported component was backed up; nothing was skipped, excluded, or failed.
- **warning**: at least one component was skipped or intentionally excluded, or container configuration was omitted.
- **error**: at least one selected mount failed to back up or the backup job failed technically.

The detailed log records each mount as `BACKED UP`, `EXCLUDED`, `SKIPPED`, or `FAILED`, including mount type, source/name, container destination, archive, size, and reason where applicable.

## Restore modes

The restore dialog supports:

- **Automatic**: use the original/existing container when found, otherwise recreate it.
- **Existing container**: restore mount data into a selected existing container.
- **Recreate container**: create a missing container from `container-inspect.json`, restore its data, then start it.

For name conflicts, ContBak can abort, replace the existing container, or create the restored container under a new name.

A recreated container uses reliable settings from Docker inspect metadata. Docker runtime IDs and automatically generated state are not copied. A single-container restore does not recreate an entire multi-service Compose stack.

## Excluding a container

```yaml
labels:
  contbak.exclude: "true"
```

ContBak excludes itself by default in the supplied Compose file.

## Release model

**Git tags are the single source of published release versions.** Development builds from `main`/pull requests identify themselves as `dev`; published images get their version from the `vX.Y.Z` tag that triggered the release workflow.

Configure these repository secrets:

```text
DOCKERHUB_USERNAME=frazon11
DOCKERHUB_TOKEN=<Docker Hub personal access token with Read & Write>
```

After a change has passed CI and been merged, create the release tag:

```bash
git tag -a vX.Y.Z -m "ContBak X.Y.Z"
git push origin vX.Y.Z
```

The workflow validates the tagged source and only then publishes:

```text
frazon11/contbak:X.Y.Z
frazon11/contbak:X.Y
frazon11/contbak:latest
frazon11/contbak:sha-<commit>
```

It also creates the matching GitHub Release automatically.

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for released changes and work currently on `main` but not yet included in a release.

## Known limitations

- Full multi-service Docker Compose stack recreation is not yet implemented.
- Backups are full TAR/Gzip archives, not incremental or deduplicated.
- Backups are not encrypted by ContBak itself.
- Jobs execute sequentially.
- Application-native database dumps remain preferable for strict transactional consistency.

## License

MIT License. See `LICENSE`.
