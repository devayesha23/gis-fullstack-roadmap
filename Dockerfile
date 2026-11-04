FROM python:3.11-slim
WORKDIR /app
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt
COPY api api
COPY web web
EXPOSE 8000
CMD ["uvicorn", "main:app", "--app-dir", "api", "--host", "0.0.0.0", "--port", "8000"]
