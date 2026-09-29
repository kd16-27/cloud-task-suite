FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements-cloud.txt ./
RUN pip install --no-cache-dir -r requirements-cloud.txt && useradd -m appuser
COPY . .
RUN mkdir -p instance && chown -R appuser:appuser /app
USER appuser
ENV APP_HOST=0.0.0.0 PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "run.py"]
