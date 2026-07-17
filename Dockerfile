FROM python:3.13-alpine

LABEL org.opencontainers.image.title="ContBak" \
      org.opencontainers.image.description="Container Backup Manager" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app
RUN apk add --no-cache tzdata
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN mkdir -p /data /backups
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080"]
