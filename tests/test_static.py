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
