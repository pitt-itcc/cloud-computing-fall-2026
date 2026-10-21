FROM ghcr.io/astral-sh/uv:0.12.23 AS uv

# Build stage: install dependencies into the Lambda task root
FROM public.ecr.aws/lambda/python:3.14 AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_INSTALLER_METADATA=1
ENV UV_LINK_MODE=copy

# Cache busts only when pyproject.toml or uv.lock change, not on app code edits
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv export --frozen --no-emit-workspace --no-dev --no-editable -o requirements.txt && \
    uv pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Final stage: the Lambda base image already runs as an unprivileged user
FROM public.ecr.aws/lambda/python:3.14

COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}
COPY ./app ${LAMBDA_TASK_ROOT}/app

CMD ["app.handler.handler"]
