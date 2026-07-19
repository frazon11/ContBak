from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_required_files_exist():
    for rel in [
        'Dockerfile', 'docker-compose.yml', 'LICENSE', 'README.md',
        'app/main.py', 'app/templates/index.html', 'app/static/style.css'
    ]:
        assert (ROOT / rel).exists(), rel

def test_public_identity_is_consistent():
    files = [ROOT/'Dockerfile', ROOT/'docker-compose.yml', ROOT/'README.md', ROOT/'.github/workflows/docker-publish.yml']
    text = '\n'.join(p.read_text(encoding='utf-8') for p in files)
    assert 'fron/contbak' not in text
    assert 'frazon11/contbak' in text
    assert 'Frazon11/ContBak' in text


def test_version_and_host_backup_path():
    main = (ROOT/'app/main.py').read_text(encoding='utf-8')
    template = (ROOT/'app/templates/index.html').read_text(encoding='utf-8')
    compose = (ROOT/'docker-compose.yml').read_text(encoding='utf-8')
    assert "VERSION='1.4.0'" in main
    assert 'HOST_BACKUP_ROOT' in main
    assert "str(host_backup_root())" in main
    assert 'Version {{ version }}' in template
    assert 'CONTBAK_BACKUP_PATH:' in compose
