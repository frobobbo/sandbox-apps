FROM python:3.13-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY patchpilot_wp ./patchpilot_wp
COPY templates ./templates

RUN pip install --no-cache-dir .
RUN mkdir -p /app/data

EXPOSE 8037
CMD ["uvicorn", "patchpilot_wp.main:app", "--host", "0.0.0.0", "--port", "8037"]
