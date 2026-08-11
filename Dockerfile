FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CKNEXUS_HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

RUN addgroup --system cknexus && adduser --system --ingroup cknexus cknexus

COPY pyproject.toml README.md ./
COPY app ./app
COPY creator_app ./creator_app
COPY services ./services
COPY migrations ./migrations
COPY main.py ./main.py

RUN python -m pip install --no-cache-dir ".[email,gateway]" \
    && mkdir -p /app/data \
    && chown -R cknexus:cknexus /app

USER cknexus
EXPOSE 8000

CMD ["python", "main.py"]

