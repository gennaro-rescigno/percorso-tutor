# ---- frontend build ----
FROM node:20.17-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build && VITE_STATIC=1 VITE_BASE=./ npx vite build --outDir dist-static --emptyOutDir

# ---- python runtime ----
FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN useradd --create-home --uid 10001 mci
WORKDIR /app
COPY backend/pyproject.toml ./backend/
COPY backend/mci ./backend/mci
RUN pip install ./backend
COPY --from=web /web/dist ./frontend/dist
COPY --from=web /web/dist-static ./frontend/static-dist
ENV MCI_FRONTEND_DIST_DIR=/app/frontend/dist
RUN mkdir -p /app/reports /app/backend/data /srv/site && chown -R mci /app/reports /app/backend/data /srv/site
USER mci
WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5).status==200 else 1)" || exit 1
CMD ["mci", "api"]
