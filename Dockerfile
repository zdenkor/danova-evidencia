FROM python:3.12-slim

WORKDIR /app

# Inštalácia závislostí
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopírovanie aplikácie
COPY . .

# Vytvorenie adresára pre dáta
RUN mkdir -p /data

# Premenné prostredia
ENV DB_PATH=/data/danova_evidencia.db
ENV FLASK_PORT=8080
ENV FLASK_HOST=0.0.0.0

# Port
EXPOSE 8080

# Spustenie
CMD ["python", "app.py"]
