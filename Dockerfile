# Image de base figée (version exacte) pour des builds reproductibles
ARG PYTHON_IMAGE=python:3.11.18-slim-trixie

# ---------- Étape 1 : dépendances installées dans un venv ----------
FROM ${PYTHON_IMAGE} AS builder

# requirements.txt pour l'API, requirements-train.txt (+ mlflow) pour le job d'entraînement
ARG REQUIREMENTS=requirements.txt
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt requirements-train.txt ./

# Optimisation : pas de bytecode, suppression des tests embarqués par les librairies et de pip lui-même
RUN pip install --no-compile -r ${REQUIREMENTS} \
    && find /opt/venv -depth -type d \( -name __pycache__ -o -name tests \) -exec rm -rf {} + \
    && pip uninstall -y pip setuptools

# ---------- Étape 2 : image d'exécution ----------
FROM ${PYTHON_IMAGE} AS runtime

LABEL org.opencontainers.image.title="express-delivery" \
      org.opencontainers.image.description="API d'éligibilité à la livraison express" \
      org.opencontainers.image.source="https://github.com/Charlyf-Data/Cloud-AI-Engineering" \
      org.opencontainers.image.licenses="MIT"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Utilisateur sans shell de connexion ni répertoire personnel ; pip retiré de l'image d'exécution
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && python -m pip uninstall -y pip setuptools wheel
WORKDIR /app

# Code et dépendances appartiennent à root : l'utilisateur app ne peut pas les modifier
COPY --from=builder /opt/venv /opt/venv
COPY src/express_delivery ./src/express_delivery
RUN mkdir data artifacts lake && chown app:app data artifacts lake

USER 10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('API_PORT', '8000') + '/health', timeout=2)" || exit 1

ENTRYPOINT ["python", "-m", "express_delivery.main"]
CMD ["serve"]
