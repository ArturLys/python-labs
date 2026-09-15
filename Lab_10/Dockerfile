# syntax=docker/dockerfile:1
# Stage 1: build the wheel from the sources (build tools never reach the runtime image)
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir build && python -m build --wheel --outdir /build/dist

# Stage 2: slim runtime with a non-root user, the wheel and the migrations only
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    LOG_LEVEL=INFO \
    DATABASE_URL=sqlite:////data/students.db \
    API_HOST=0.0.0.0 \
    API_PORT=8000
RUN useradd --create-home --uid 1000 app && mkdir -p /data && chown app:app /data
WORKDIR /app
COPY --from=builder /build/dist/*.whl /tmp/
COPY alembic.ini ./
COPY migrations ./migrations
RUN pip install --no-cache-dir "student-manager[api] @ file://$(ls /tmp/*.whl)" && rm -f /tmp/*.whl
USER app
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"
# migrations run at start-up, then the API (API_TOKEN must be passed with -e / an env file)
CMD ["sh", "-c", "alembic upgrade head && student-api serve"]
