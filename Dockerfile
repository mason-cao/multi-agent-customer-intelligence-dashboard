FROM python:3.11-slim

WORKDIR /app

COPY backend/ ./backend/
COPY scripts/ ./scripts/

RUN mkdir -p /app/data/workspaces

RUN cd backend && pip install --no-cache-dir .

WORKDIR /app/backend

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
