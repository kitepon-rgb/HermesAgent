FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_NO_CACHE=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY DOCS/prompts ./DOCS/prompts

RUN uv pip install --system --no-cache .

# uv pip install 後はコード本体が /usr/local/lib/python3.12/site-packages/ に移るため、
# DOCS/prompts への相対参照が崩れる。env で絶対パスを与える。
ENV X_HERMES_MCP_PROMPTS_DIR=/app/DOCS/prompts

EXPOSE 65432

# host の ~/.hermes/ を bind mount できるよう、コンテナ内に同じパスを用意。
# (mount で被さるので空ディレクトリで OK。)
RUN mkdir -p /home/kite/.hermes

HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('127.0.0.1', 65432), timeout=2).close()" || exit 1

CMD ["x-hermes-mcp"]
