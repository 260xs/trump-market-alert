#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/trump-market-alert}"
SERVICE_USER="${SERVICE_USER:-market-alert}"
ENV_FILE="${ENV_FILE:-/etc/market-alert.env}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this installer with sudo/root."
  exit 1
fi

if [ ! -d "${APP_DIR}" ]; then
  mkdir -p "${APP_DIR}"
fi

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

chown -R "${SERVICE_USER}:${SERVICE_USER}" "${APP_DIR}"

cd "${APP_DIR}"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt -r requirements-stocks.txt

mkdir -p data
chown -R "${SERVICE_USER}:${SERVICE_USER}" data

if [ ! -f "${ENV_FILE}" ]; then
  cp deploy/market-alert.env.example "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  echo "Created ${ENV_FILE}. Edit it and add your real secrets before starting the service."
else
  chmod 600 "${ENV_FILE}"
fi

cp deploy/market-alert.service /etc/systemd/system/market-alert.service
systemctl daemon-reload
systemctl enable market-alert.service

echo "Install finished."
echo "Next:"
echo "1. Edit ${ENV_FILE}"
echo "2. Run: python ${APP_DIR}/scripts/check_setup.py --env-file ${ENV_FILE} --clear-telegram-webhook --send-telegram-test"
echo "3. Run: sudo systemctl restart market-alert.service"
echo "4. Send /menu to your Telegram bot"
