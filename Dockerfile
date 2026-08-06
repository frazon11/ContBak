FROM python:3.13-slim
LABEL org.opencontainers.image.title="ContBak" \
      org.opencontainers.image.description="Web-based backup and restore manager for Docker containers, volumes and bind mounts" \
      org.opencontainers.image.version="1.5.1" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/Frazon11/ContBak" \
      org.opencontainers.image.url="https://github.com/Frazon11/ContBak"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app /app
RUN sed -i "s/VERSION='1.4.1'/VERSION='1.5.1'/" /app/main.py \
    && python -c "from pathlib import Path; p=Path('/app/main.py'); s=p.read_text(); old=\"manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8')); c=client.containers.get(manifest['id']); was_running=c.status=='running'\"; new=\"manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8'))\\n  try:c=client.containers.get(manifest.get('id'))\\n  except Exception:\\n   name=manifest.get('name') or manifest.get('container_name')\\n   if not name:raise RuntimeError('Backup manifest contains no container name.')\\n   try:c=client.containers.get(name)\\n   except Exception as exc:raise RuntimeError(f'Container {name} was not found. Create or rename the target container before restoring.') from exc\\n  was_running=c.status=='running'\"; assert old in s, 'restore target pattern not found'; p.write_text(s.replace(old,new),encoding='utf-8')" \
    && cat /app/static/releases.js >> /app/static/app.js \
    && cat /app/static/import-restore.js >> /app/static/app.js \
    && mkdir -p /data /backups
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
