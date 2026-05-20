FROM python:3.12-slim

WORKDIR /app

# Install deps first (cached layer)
COPY backend-fastapi/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend-fastapi/ .

# Copy shared business logic (plan rules, etc.)
COPY src/ ./src/

ENV PORT=8080
EXPOSE 8080

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
