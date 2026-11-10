#!/usr/bin/env bash
# Backup diário do volume de dados. Rodar no host, por exemplo via cron:
#   0 3 * * * /home/ubuntu/biotracex/deploy/backup.sh
# Mantém os últimos 7 backups.
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-$HOME/biotracex-backups}"
mkdir -p "$BACKUP_DIR"

# O volume do compose tem o nome do projeto + app_data (ex.: deploy_app_data)
VOLUME="$(docker volume ls --format '{{.Name}}' | grep 'app_data$' | head -n1)"
if [[ -z "$VOLUME" ]]; then
  echo "Volume app_data não encontrado" >&2
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
docker run --rm -v "$VOLUME":/data:ro -v "$BACKUP_DIR":/backup alpine \
  tar czf "/backup/app_data-$STAMP.tar.gz" -C /data .

# Mantém só os 7 mais recentes
ls -1t "$BACKUP_DIR"/app_data-*.tar.gz | tail -n +8 | xargs -r rm -f
echo "Backup criado: $BACKUP_DIR/app_data-$STAMP.tar.gz"
