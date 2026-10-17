FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
# Readable by the non-root user even when the checkout was made with a strict umask (077).
RUN chmod a+r pyproject.toml uv.lock && uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
RUN chmod -R a+rX src alembic alembic.ini && uv sync --frozen --no-dev && useradd --create-home --uid 10001 monetae
ENV PATH="/app/.venv/bin:$PATH"
USER monetae
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn monetae.api.main:app --host 0.0.0.0 --port 8000"]
