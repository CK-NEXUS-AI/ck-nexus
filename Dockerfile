FROM python:3.12.16-alpine3.24@sha256:e6dae589c1c05976188fd3bd019afd091445fc533ed2ea29001beddc7368a9c8

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CKNEXUS_HOST=0.0.0.0 \
    PORT=8000 \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

RUN apk upgrade --no-cache

RUN addgroup -S cknexus && adduser -S -G cknexus cknexus \
    && python -m pip install --no-cache-dir --upgrade pip==26.3 setuptools==83.0.0 uv==0.13.7

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
