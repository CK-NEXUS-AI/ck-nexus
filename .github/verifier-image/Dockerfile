ARG BASE_IMAGE=python@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254
FROM ${BASE_IMAGE}

ARG UV_VERSION=0.12.5
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/cknexus-venv \
    PATH=/opt/cknexus-venv/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir "uv==${UV_VERSION}" \
    && groupadd --gid 65532 verifier \
    && useradd --uid 65532 --gid 65532 --no-create-home --home-dir /nonexistent \
       --shell /usr/sbin/nologin verifier

WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --all-extras --dev --frozen --no-install-project

COPY .github/verifier-image/verify /cknexus/verify
RUN chmod 0555 /cknexus/verify \
    && mkdir -p /workspace \
    && chmod 0777 /workspace

WORKDIR /workspace
USER 65532:65532
ENTRYPOINT ["/cknexus/verify"]
