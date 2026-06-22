FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir . uvicorn
EXPOSE 8020
CMD ["uvicorn", "wp_fleetops.main:app", "--host", "0.0.0.0", "--port", "8020"]
