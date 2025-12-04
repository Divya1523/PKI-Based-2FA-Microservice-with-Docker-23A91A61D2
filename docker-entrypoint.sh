set -euo pipefail
echo "Entrypoint: TZ=${TZ:-UTC}"
if [ -f /etc/cron.d/app-cron ]; then
  chmod 0644 /etc/cron.d/app-cron || true
  crontab /etc/cron.d/app-cron || true
fi
if command -v cron >/dev/null 2>&1; then
  echo "Starting cron..."
  cron || echo "cron start returned non-zero (ignored)"
fi
mkdir -p /var/run
chown root:root /var/run || true
chmod 755 /var/run || true
if [ "$(id -u)" -eq 0 ] && command -v gosu >/dev/null 2>&1; then
  echo "Switching to appuser and executing: $*"
  exec gosu appuser "$@"
else
  echo "Executing (no gosu): $*"
  exec "$@"
fi
