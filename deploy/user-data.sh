#!/usr/bin/env bash
# EC2 user-data: paste this into "Advanced details -> User data" when launching
# the instance. It runs once, as root, on first boot.
#
# Target AMI: Ubuntu Server 24.04 LTS. It ships Python 3.12, and this codebase
# needs 3.10 or newer (it uses PEP 604 `X | None` annotations). Amazon Linux
# 2023 defaults to Python 3.9 and would need an extra install step.
set -euxo pipefail

REPO="https://github.com/manyamharshitha/EUV-OPTIMIZATION.git"
APP_DIR="/opt/euv-optimizer"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git nginx python3

# Dedicated unprivileged account. It owns nothing but the app directory and
# cannot log in.
if ! id euv >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin euv
fi

# Clone fresh, or update in place if the instance is being re-provisioned.
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch --depth 1 origin main
  git -C "$APP_DIR" reset --hard origin/main
else
  rm -rf "$APP_DIR"
  git clone --depth 1 "$REPO" "$APP_DIR"
fi
chown -R euv:euv "$APP_DIR"

# Fail loudly here rather than looping in systemd if the Python is too old.
python3 - <<'PY'
import sys
assert sys.version_info >= (3, 10), f"need Python 3.10+, found {sys.version}"
print(f"python OK: {sys.version.split()[0]}")
PY

install -m 644 "$APP_DIR/deploy/euv-optimizer.service" /etc/systemd/system/euv-optimizer.service

# Replace nginx's default site so ours is the one that answers on port 80.
install -m 644 "$APP_DIR/deploy/nginx-euv.conf" /etc/nginx/sites-available/euv
ln -sf /etc/nginx/sites-available/euv /etc/nginx/sites-enabled/euv
rm -f /etc/nginx/sites-enabled/default
nginx -t

systemctl daemon-reload
systemctl enable --now euv-optimizer
systemctl restart nginx

# Wait for the app to answer before declaring success, so a failure shows up
# in the boot log instead of surfacing later as a blank page.
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1/api/health >/dev/null; then
    echo "euv-optimizer is serving"
    exit 0
  fi
  sleep 2
done

echo "app did not become healthy in 60s" >&2
systemctl status euv-optimizer --no-pager >&2 || true
journalctl -u euv-optimizer -n 50 --no-pager >&2 || true
exit 1
