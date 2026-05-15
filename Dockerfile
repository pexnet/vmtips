# ── Frontend build stage ─────────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build


# ── Production stage ─────────────────────────────────
FROM python:3.11-slim AS production

WORKDIR /app

# Create data directory for SQLite
RUN mkdir -p /app/data

# Backend deps
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend code
COPY backend/ .

# Frontend static files
COPY --from=frontend-build /app/dist ./static

# Make startup script executable
RUN chmod +x start.sh

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV STATIC_DIR=/app/static
ENV DATABASE_URL=sqlite:///app/data/vmtips.db

CMD ["./start.sh"]
