FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir . uvicorn
EXPOSE 8010
CMD ["uvicorn", "wp_carepulse.main:app", "--host", "0.0.0.0", "--port", "8010"]
