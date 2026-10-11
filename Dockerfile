FROM python:3.12-slim@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CKNEXUS_HOST=0.0.0.0 \
    PORT=8000 \
    CKNEXUS_DEVELOPMENT_STATUS_DB=/app/data/development-status.sqlite3 \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

RUN addgroup --system cknexus && adduser --system --ingroup cknexus cknexus \
    && python -m pip install --no-cache-dir uv==0.12.4

COPY pyproject.toml uv.lock README.md ./
COPY app ./app
COPY creator_app ./creator_app
COPY services ./services
COPY gateway ./gateway
COPY orchestration ./orchestration
COPY idea_engine ./idea_engine
COPY migrations ./migrations
COPY main.py ./main.py

RUN uv lock --check \
    && uv sync --frozen --no-dev --no-editable \
      --extra email --extra gateway --extra billing --extra github-app \
    && mkdir -p /app/data \
    && chown -R cknexus:cknexus /app

USER cknexus
EXPOSE 8000

CMD ["python", "-m", "creator_app.unified"]
