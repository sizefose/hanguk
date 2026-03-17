#!/bin/sh
set -e

# We avoid using mysql/mysqladmin CLIs here because Debian's "default-mysql-client"
# can be MariaDB-based and doesn't support the same SSL flags as Oracle MySQL clients.
# Instead, we use the same MySQL driver Django uses (mysqlclient/MySQLdb).
export MYSQL_HOST="${MYSQL_HOST:-mysql}"
export MYSQL_PORT="${MYSQL_PORT:-3306}"
export MYSQL_DATABASE="${MYSQL_DATABASE:-hanguk}"
export MYSQL_USER="${MYSQL_USER:-hanguk}"
export MYSQL_PASSWORD="${MYSQL_PASSWORD:-hanguk}"
export DB_WAIT_MAX_ATTEMPTS="${DB_WAIT_MAX_ATTEMPTS:-120}"
export DJANGO_AUTO_MIGRATE="${DJANGO_AUTO_MIGRATE:-true}"

python - <<'PY'
import os
import sys
import time

import MySQLdb  # provided by mysqlclient

host = os.environ["MYSQL_HOST"]
port = int(os.environ["MYSQL_PORT"])
db = os.environ["MYSQL_DATABASE"]
user = os.environ["MYSQL_USER"]
password = os.environ["MYSQL_PASSWORD"]
max_attempts = int(os.environ.get("DB_WAIT_MAX_ATTEMPTS", "120"))

last_error = None

for attempt in range(1, max_attempts + 1):
    try:
        conn = MySQLdb.connect(
            host=host,
            port=port,
            user=user,
            passwd=password,
            db=db,
            charset="utf8mb4",
        )
        conn.close()
        break
    except Exception as exc:
        err = f"{exc.__class__.__name__}: {exc}" if exc else "unknown error"
        if err != last_error:
            print(f"Waiting for MySQL at {host}:{port}... ({attempt}/{max_attempts}) {err}")
            last_error = err
        else:
            print(f"Waiting for MySQL at {host}:{port}... ({attempt}/{max_attempts})")
        time.sleep(2)
else:
    print(f"Timed out waiting for MySQL at {host}:{port}.", file=sys.stderr)
    sys.exit(1)
PY

if [ "$DJANGO_AUTO_MIGRATE" = "true" ] || [ "$DJANGO_AUTO_MIGRATE" = "1" ]; then
  if [ -f "manage.py" ]; then
    echo "Applying Django migrations..."
    python manage.py migrate --noinput
  fi
fi

echo "MySQL is up. Starting server..."
exec "$@"
