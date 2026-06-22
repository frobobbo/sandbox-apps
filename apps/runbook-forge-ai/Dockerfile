FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RUNBOOK_FORGE_DB=/app/data/runbooks.sqlite3

WORKDIR /app
COPY pyproject.toml README.md ./
COPY runbook_forge ./runbook_forge
COPY templates ./templates
RUN pip install --no-cache-dir .
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["uvicorn", "runbook_forge.main:app", "--host", "0.0.0.0", "--port", "8000"]
