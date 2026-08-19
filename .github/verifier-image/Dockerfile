ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG UV_VERSION=0.12.5
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/cknexus-venv \
    PATH=/opt/cknexus-venv/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --all-extras --dev --frozen --no-install-project

COPY .github/verifier-image/verify /cknexus/verify
RUN chmod 0555 /cknexus/verify \
    && mkdir -p /workspace \
    && chmod 0777 /workspace

WORKDIR /workspace
ENTRYPOINT ["/cknexus/verify"]
