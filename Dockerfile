# Production: single container serving both frontend and backend
# Frontend is built to static files, served by backend's static middleware

# --- Build stage for frontend ---
FROM node:20-slim AS frontend-build

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# --- Runtime stage ---
FROM python:3.12-slim

WORKDIR /app

# Install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy built frontend static files into backend's static directory
COPY --from=frontend-build /app/dist ./static

# Create data directory for SQLite
RUN mkdir -p /data

# Environment defaults (override in production)
ENV DATABASE_URL=sqlite:////data/vmtips.db
ENV JWT_SECRET_KEY=change-me-in-production
ENV JWT_ALGORITHM=HS256
ENV JWT_EXPIRATION_HOURS=168
ENV ADMIN_EMAIL=admin@example.com
ENV WORLD_CUP_JSON_URL=https://worldcupjson.net/matches
ENV CORS_ORIGINS=""
ENV STATIC_DIR=/app/static

EXPOSE 8000

# Run migrations/seed on startup then start server
CMD python -c "from database import Base, engine; Base.metadata.create_all(bind=engine)" && \
    python seed.py 2>/dev/null || true && \
    uvicorn main:app --host 0.0.0.0 --port 8000
