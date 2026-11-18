# ---- test stage: runs the moto-mocked tests, fails the build if any fail ----
FROM python:3.12-slim AS test

WORKDIR /app
COPY src/ src/
COPY tests/ tests/

RUN pip install --no-cache-dir boto3 "moto[s3]" pytest \
    && pytest tests/ -v

# ---- runtime stage: only the handler, on the lambda base image ----
FROM public.ecr.aws/lambda/python:3.12

COPY src/workers.py ${LAMBDA_TASK_ROOT}/

# default handler; each lambda overrides via image_config.command
CMD ["workers.thumbnail_handler"]
