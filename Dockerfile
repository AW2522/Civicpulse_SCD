# syntax=docker/dockerfile:1

FROM python:3.12-slim AS build

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

FROM python:3.12-slim AS serve

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -m appuser

COPY --from=build /opt/venv /opt/venv
COPY backend/ /app

RUN chown -R appuser:appuser /app /home/appuser /opt/venv

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
