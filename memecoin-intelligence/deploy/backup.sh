#!/bin/sh
# Daily compressed pg_dump, keeps the last 14 days.
set -eu
while true; do
  f="/backups/mci-$(date -u +%Y%m%d-%H%M).sql.gz"
  pg_dump -h db -U mci mci | gzip > "$f" && echo "backup ok: $f" || echo "backup FAILED"
  find /backups -name 'mci-*.sql.gz' -mtime +14 -delete
  sleep 86400
done
