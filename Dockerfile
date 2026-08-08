FROM python:3.13-slim

ARG APP_VERSION=dev

LABEL org.opencontainers.image.title="ContBak" \
      org.opencontainers.image.description="Web-based backup and restore manager for Docker containers, volumes and bind mounts" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/Frazon11/ContBak" \
      org.opencontainers.image.url="https://github.com/Frazon11/ContBak"

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app /app
RUN sed -i "s/VERSION='1.4.1'/VERSION='${APP_VERSION}'/" /app/main.py \
    && python /app/patch_restore_v152.py \
    && python /app/patch_restore_v153.py \
    && python /app/patch_restore_v160.py \
    && python /app/patch_restore_v161.py \
    && python /app/patch_backup_v170.py \
    && python /app/patch_mounts_v171.py \
    && rm /app/patch_restore_v152.py /app/patch_restore_v153.py /app/patch_restore_v160.py /app/patch_restore_v161.py /app/patch_backup_v170.py /app/patch_mounts_v171.py \
    && cat /app/static/releases.js >> /app/static/app.js \
    && cat /app/static/import-restore.js >> /app/static/app.js \
    && cat /app/static/restore-recreate.js >> /app/static/app.js \
    && cat /app/static/backup-options.js >> /app/static/app.js \
    && python -m py_compile /app/main.py \
    && mkdir -p /data /backups

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
