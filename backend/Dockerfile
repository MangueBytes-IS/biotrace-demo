FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY ncbi_collector.py .

ENV FLASK_APP=app.py
EXPOSE 5000

# Um único worker: a coleta roda em thread dentro do processo e o estado fica em memória (DATA_LOCK)
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:5000", "app:app"]
