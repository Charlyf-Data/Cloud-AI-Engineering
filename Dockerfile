# ---------- Étape 1 : dépendances installées dans un venv ----------
FROM python:3.11-slim AS builder

# requirements.txt pour l'API, requirements-train.txt (+ mlflow) pour le job d'entraînement
ARG REQUIREMENTS=requirements.txt
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt requirements-train.txt ./
RUN pip install -r ${REQUIREMENTS}

# ---------- Étape 2 : image d'exécution ----------
FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 app
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY src/express_delivery ./src/express_delivery
RUN mkdir -p data artifacts && chown -R app:app /app

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('API_PORT', '8000') + '/health', timeout=2)" || exit 1

ENTRYPOINT ["python", "-m", "express_delivery.main"]
CMD ["serve"]
