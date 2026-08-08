FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN addgroup --system cknexus && adduser --system --ingroup cknexus cknexus
COPY pyproject.toml README.md ./
COPY gateway ./gateway
COPY orchestration ./orchestration
COPY idea_engine ./idea_engine
RUN python -m pip install --no-cache-dir ".[gateway]" && chown -R cknexus:cknexus /app
USER cknexus
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
