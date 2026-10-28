#!/bin/sh
# Check every link of the running site with linkchecker (make check-site-links).
# The site runs on a new database in .cache/site with the user admin and the
# demo project, so no GitHub is needed. Its pages are crawled signed in as
# admin@example.com.
set -e
PORT=8765  # also in linkcheckerrc, for signing in
HERE=$(cd "$(dirname "$0")" && pwd)
SITE="$HERE/../../.cache/site"
rm -rf "$SITE"
mkdir -p "$SITE"
export DATA_DIR="$SITE" PRODUCTION=false DEBUG=0 FETCH_WORKER=inline ALLOWED_HOSTS=127.0.0.1
uv run python manage.py migrate -v0
uv run python manage.py ensure_superuser admin@example.com:admin
uv run python manage.py demo_data admin@example.com
uv run python manage.py runserver --noreload --insecure "127.0.0.1:$PORT" > "$SITE/server.log" 2>&1 &
SERVER=$!
trap 'kill $SERVER' EXIT
for _ in $(seq 60); do
    curl -sf "http://127.0.0.1:$PORT/" > /dev/null && break
    sleep 1
done
uvx --quiet linkchecker==10.6.0 --config "$HERE/linkcheckerrc" "http://127.0.0.1:$PORT/"
# the pages behind the sign in were checked, too
grep -q '"POST /accounts/login/ HTTP/1.1" 302' "$SITE/server.log" || {
    echo "linkchecker could not sign in as admin@example.com"
    exit 1
}
