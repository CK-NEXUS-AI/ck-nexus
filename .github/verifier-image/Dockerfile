ARG BASE_IMAGE=python@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337
FROM ${BASE_IMAGE}

ARG UV_VERSION=0.13.7
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
