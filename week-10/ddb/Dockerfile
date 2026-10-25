FROM ghcr.io/astral-sh/uv:0.12.23 AS uv

FROM python:3.14-slim AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_INSTALLER_METADATA=1
ENV UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv export --frozen --no-dev --no-editable -o requirements.txt && \
    uv pip install -r requirements.txt --target /deps

FROM python:3.14-slim

WORKDIR /app
COPY --from=builder /deps /deps
ENV PYTHONPATH=/deps
COPY load.py demo.py ./

ENTRYPOINT ["python3"]
