FROM python:3.13-slim

# licenses
COPY LICENSE /LICENSE

# server environment variables
EXPOSE 5000
ENV PORT=5000
# one process holds pandas, matplotlib, lifelines and statsmodels: about 300 MB
ENV WORKERS=1
ENV THREADS=4
# the fetch worker runs as a process of its own in this container
# (docker/start-service.sh); external-separate-container for its own container
ENV FETCH_WORKER=external-http-container
ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=true
# the nginx of the container adds the address of the visitor to X-Forwarded-For
ENV TRUSTED_PROXIES=1

# nginx in front of gunicorn serves the static files (docker/nginx.conf)
RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app

# Install packages. The versions are locked in uv.lock.
COPY pyproject.toml uv.lock* README.md ./
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv sync --no-dev --no-install-project --frozen || uv sync --no-dev --no-install-project

# Add the app
COPY manage.py REUSE.toml ./
COPY community_insights community_insights
COPY static static
COPY locale locale
COPY docker/start-service.sh .
COPY docker/nginx.conf docker/nginx.conf
# throwaway keys: nothing secret is written into the image
RUN SECRET_KEY=build SALT_KEY=build python manage.py collectstatic --noinput

VOLUME /app/data
HEALTHCHECK CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:%s/health/' % os.environ['PORT'])"
ENTRYPOINT ["/bin/sh", "start-service.sh"]
