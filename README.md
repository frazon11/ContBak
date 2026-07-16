# ContBak

ContBak (ContainerBackup) is a lightweight WebUI for backing up and restoring Docker container mounts.

## Image

```text
fron/contbak:0.1.0
```

## Features

- discovers Docker containers, named volumes and bind mounts
- backup one container or all containers
- optional container stop for improved consistency
- restore from the WebUI
- daily schedules per container
- configurable retention
- stores Docker inspect metadata and backup manifests
- responsive dashboard
- supports `linux/amd64` and `linux/arm64`

## Quick start

```bash
cp .env.example .env
docker compose up -d
```

Open `http://HOST:8787`.

## Synology paths

The included Compose file uses:

```text
/volume1/docker/contbak/config
/volume1/docker/contbak/backups
```

## Environment variables

| Variable | Default | Description |
|---|---:|---|
| `TZ` | `Europe/Brussels` | Timezone |
| `CONTBAK_USER` | none recommended | WebUI username |
| `CONTBAK_PASSWORD` | none recommended | WebUI password |
| `HELPER_IMAGE` | `alpine:3.22` | Temporary backup helper image |
| `STOP_CONTAINERS` | `true` | Stop running containers during backup |
| `RETENTION_COUNT` | `7` | Backups retained per container |

## Security warning

Mounting `/var/run/docker.sock` gives ContBak extensive control over the Docker host. Do not expose the WebUI directly to the internet. Use a VPN or protected reverse proxy and strong credentials.

## Publishing a release

Create these GitHub repository secrets:

- `DOCKERHUB_USERNAME` = `fron`
- `DOCKERHUB_TOKEN` = a Docker Hub access token

Then create and push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions builds and publishes:

- `fron/contbak:0.1.0`
- `fron/contbak:0.1`
- `fron/contbak:latest`

## License

MIT
