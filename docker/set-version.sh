#!/bin/sh
# Writes build metadata into community_insights/version.json, like myco-webshop.
# Run before `docker build` so the generated file is copied into the image.
# Safe to call outside CI: falls back to git for the commit.
set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
VERSION_FILE="${VERSION_FILE:-$PROJECT_ROOT/community_insights/version.json}"

if [ -n "${GITHUB_SHA:-}" ]; then
    FULL_COMMIT="$GITHUB_SHA"
else
    FULL_COMMIT=$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
fi
COMMIT=$(echo "$FULL_COMMIT" | cut -c1-7)

# the release tag (v1.2.3) or the version of pyproject.toml
TAG=""
if [ "${GITHUB_REF_TYPE:-}" = "tag" ]; then
    TAG="${GITHUB_REF_NAME}"
    VERSION="${GITHUB_REF_NAME#v}"
else
    VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' "$PROJECT_ROOT/pyproject.toml" | head -n 1)
fi

REPO="${GITHUB_REPOSITORY:-PyCalendar/community-insights}"
SERVER="${GITHUB_SERVER_URL:-https://github.com}"
BUILD_URL=""
if [ -n "${GITHUB_RUN_ID:-}" ]; then
    BUILD_URL="${SERVER}/${REPO}/actions/runs/${GITHUB_RUN_ID}"
fi

cat > "$VERSION_FILE" <<JSON
{
  "version": "${VERSION}",
  "built": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "commit": "${COMMIT}",
  "commit_full": "${FULL_COMMIT}",
  "tag": "${TAG}",
  "build_url": "${BUILD_URL}"
}
JSON

echo "Version set: ${VERSION} ${COMMIT}"
