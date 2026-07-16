FROM python:3.13-slim
LABEL org.opencontainers.image.title="ContBak" \
      org.opencontainers.image.description="Web-based backup and restore manager for Docker containers, volumes and bind mounts" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/Frazon11/ContBak" \
      org.opencontainers.image.url="https://github.com/Frazon11/ContBak"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app /app
RUN mkdir -p /data /backups
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
