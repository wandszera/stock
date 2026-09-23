FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

RUN addgroup --system stock && adduser --system --ingroup stock stock

COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --requirement requirements.txt

COPY backend/ ./
COPY frontend/ /app/frontend/

RUN chown -R stock:stock /app
USER stock

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os, urllib.request; host=os.environ['TRUSTED_HOSTS'].split(',')[0].strip(); request=urllib.request.Request('http://127.0.0.1:8000/ready', headers={'Host': host}); urllib.request.urlopen(request, timeout=3)" || exit 1

CMD ["sh", "-c", "python -m alembic upgrade head && exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-127.0.0.1} --workers=${WEB_CONCURRENCY:-1} --no-access-log"]
