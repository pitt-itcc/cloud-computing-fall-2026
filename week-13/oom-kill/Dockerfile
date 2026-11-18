# ---- build stage: install deps into a venv ----
FROM python:3.12-slim AS build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir fastapi uvicorn

# ---- runtime stage: copy the venv + app code ----
FROM python:3.12-slim

COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY src/app.py /app/app.py

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app"]
