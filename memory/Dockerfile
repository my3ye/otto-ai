FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . ./memory/

# Set Python path so `memory` package is importable
ENV PYTHONPATH=/app

EXPOSE 8100

CMD ["uvicorn", "memory.api:app", "--host", "0.0.0.0", "--port", "8100"]
