FROM python:3.11-slim AS builder
WORKDIR /app
COPY libs/py-common /app/libs/py-common
COPY services/document-service /app/services/document-service
RUN pip install --no-cache-dir /app/libs/py-common /app/services/document-service

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY services/document-service/src /app/src
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser
EXPOSE 8001
CMD ["uvicorn", "document_service.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8001"]
