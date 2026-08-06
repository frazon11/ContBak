from pathlib import Path


def test_release_version_is_consistent():
    version = Path("VERSION").read_text(encoding="utf-8").strip()
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert version == "1.5.0"
    assert f'org.opencontainers.image.version="{version}"' in dockerfile
    assert f"VERSION='{version}'" in dockerfile


def test_compose_uses_deployment_variables():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "${CONTBAK_VERSION:-latest}" in compose
    assert "${WEB_PORT:-8787}:8080" in compose
    assert "${CONTBAK_BASE_PATH:-/volume1/docker/contbak}/config:/data" in compose
    assert "${CONTBAK_BASE_PATH:-/volume1/docker/contbak}/backups:/backups" in compose


def test_python_source_compiles():
    source = Path("app/main.py").read_text(encoding="utf-8")
    compile(source, "app/main.py", "exec")
