FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY restoreproof ./restoreproof
COPY templates ./templates
RUN pip install --no-cache-dir . uvicorn
ENV RESTOREPROOF_DB=/data/restoreproof.sqlite3
VOLUME ["/data"]
EXPOSE 8010
CMD ["uvicorn", "restoreproof.main:app", "--host", "0.0.0.0", "--port", "8010"]
