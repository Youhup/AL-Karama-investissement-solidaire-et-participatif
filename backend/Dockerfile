FROM python:3.12-slim

# Dépendances système : Tesseract (OCR fr + ar, contexte marocain) et
# Poppler (rasterisation des PDF scannés pour pdf2image).
# libpq5 suffit à l'exécution : psycopg2-binary embarque déjà le driver
# compilé, on n'a donc pas besoin de gcc / libpq-dev.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-fra \
        tesseract-ocr-ara \
        poppler-utils \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiées séparément pour profiter du cache Docker : les dépendances ne sont
# réinstallées que si requirements.txt change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Dossier des documents téléversés (monté en volume dans docker-compose)
RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
