FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app
RUN mkdir -p /app/instance
ARG PACKAGE_MANAGER=uv
RUN if [ "$PACKAGE_MANAGER" = "uv" ]; then \
        uv sync --no-dev; \
    elif [ "$PACKAGE_MANAGER" = "pip" ]; then \
        python -m venv .venv && .venv/bin/python -m pip install -r requirements.txt; \
    else \
        echo "PACKAGE_MANAGER must be uv or pip" >&2 && exit 1; \
    fi

EXPOSE 5000

ENV FLASK_ENV=production
ENV PORT=5000

CMD ["/app/.venv/bin/python", "main.py"]
