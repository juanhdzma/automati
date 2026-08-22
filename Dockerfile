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

# El servicio no necesita root para nada, y no escribe en disco.
RUN useradd --create-home --uid 1000 automati
USER automati

EXPOSE 8000

CMD ["uvicorn", "automati.main:app", "--host", "0.0.0.0", "--port", "8000"]
