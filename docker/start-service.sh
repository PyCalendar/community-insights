#!/bin/sh
# Create or update the database, then serve: nginx in front (static files,
# port $PORT), gunicorn behind it on 127.0.0.1:8000, like myco-webshop. With
# FETCH_WORKER=external-http-container (the default of the image) the fetch
# worker runs here as a process of its own, started again if it stops; with
# external-separate-container it runs in the worker service of the compose file.
set -e
# migrate, empty the cache of the statistics, DEFAULT_SUPERUSER, and stop if a
# superuser has a default password: in one process, which starts faster
python manage.py prepare
if [ "$FETCH_WORKER" = "external-http-container" ]; then
    (while true; do python manage.py fetch_worker || true; sleep 5; done) &
fi
sed "s/LISTEN_PORT/${PORT}/g" /app/docker/nginx.conf > /tmp/nginx.conf
nginx -c /tmp/nginx.conf
exec gunicorn community_insights.wsgi -w "$WORKERS" --threads "$THREADS" -b "127.0.0.1:8000" --access-logfile -
