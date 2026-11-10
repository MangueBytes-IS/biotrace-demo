# Imagem única para o Hugging Face Spaces: compila o frontend e serve tudo pelo Flask/gunicorn
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
# Vazio = o site chama a API na mesma origem (/api/...)
ENV VITE_API_URL=""
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY ncbi_collector.py .
COPY --from=frontend /app/dist ./static
# O serviço gratuito roda sem permissões de root: os dados precisam ser graváveis
RUN mkdir -p /app/analyses && chmod -R a+rwX /app
ENV PORT=7860 \
    STATIC_DIR=/app/static \
    DATA_FILE=/app/data.json \
    ANALYSES_DIR=/app/analyses
EXPOSE 7860
# Um único worker: a coleta roda em thread e o estado fica em memória
CMD gunicorn -w 1 --threads 8 -b 0.0.0.0:${PORT} app:app
