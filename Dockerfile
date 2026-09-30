FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    API_PORT=8000

WORKDIR /srv

RUN pip install poetry \
    && poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

COPY app ./app
COPY departments.yaml ./departments.yaml

RUN useradd --system --no-create-home app
USER app

EXPOSE ${API_PORT}

HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=30 \
    CMD ["python", "-c", "import os, urllib.request as u; from app.settings import settings; u.urlopen(f'http://localhost:{os.environ[\"API_PORT\"]}{settings.api_prefix}/health', timeout=4)"]

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT}"]
