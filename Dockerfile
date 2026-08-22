FROM python:3.12-slim

# PYTHONUNBUFFERED para que los logs de uvicorn salgan en tiempo real en Portainer,
# sin quedarse en el buffer hasta que el container muera.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Las dependencias van en su propia capa: mientras requirements.txt no cambie,
# Docker reusa esta capa y no reinstala nada al editar el codigo.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

# El servicio no necesita root. Solo escribe en /data (SQLite de los jobs), que
# se crea y chownea aca: si el volumen lo montara Docker sin dueno, el proceso
# non-root reventaria con "attempt to write a readonly database".
RUN useradd --create-home --uid 1000 automati \
    && mkdir -p /data \
    && chown automati:automati /data
USER automati

VOLUME ["/data"]

EXPOSE 8000

CMD ["uvicorn", "automati.main:app", "--host", "0.0.0.0", "--port", "8000"]
