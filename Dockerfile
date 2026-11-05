FROM python:3.12.16-slim-trixie@sha256:e695ab189fa2d082b1c61c69a6b888a5adeca61ceeccad107b1ed2a125721a9e AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

RUN python -m pip install --no-cache-dir --upgrade pip==26.3 setuptools==84.2.1 uv==0.13.7

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
    && uv pip check --python /app/.venv/bin/python \
    && mkdir -p /app/data \
    && chown -R 10001:10001 /app

FROM python:3.12.16-slim-trixie@sha256:e695ab189fa2d082b1c61c69a6b888a5adeca61ceeccad107b1ed2a125721a9e AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CKNEXUS_HOST=0.0.0.0 \
    PORT=8000 \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

RUN printf 'cknexus:x:10001:10001:CK-NEXUS runtime:/nonexistent:/usr/sbin/nologin\n' >> /etc/passwd \
    && printf 'cknexus:x:10001:\n' >> /etc/group \
    && rm -rf /usr/local/lib/python3.12/site-packages/pip \
       /usr/local/lib/python3.12/site-packages/pip-*.dist-info \
       /usr/local/lib/python3.12/site-packages/setuptools \
       /usr/local/lib/python3.12/site-packages/setuptools-*.dist-info \
       /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.12 \
       /usr/local/bin/uv /usr/local/bin/uvx \
    && mkdir -p /app/data \
    && chown -R 10001:10001 /app

COPY --from=builder --chown=10001:10001 /app /app

USER cknexus
EXPOSE 8000

CMD ["python", "-m", "creator_app.unified"]
