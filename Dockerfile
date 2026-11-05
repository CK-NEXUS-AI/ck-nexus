FROM python:3.12.16-slim-bookworm@sha256:62ed8e07e544e8555c5d93748d5275015136b7f5c52b5e8679b4de339c3779d3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CKNEXUS_HOST=0.0.0.0 \
    PORT=8000 \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

RUN addgroup --system cknexus && adduser --system --ingroup cknexus cknexus \
    && apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir uv==0.13.4

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
