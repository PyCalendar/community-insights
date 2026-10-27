"""The health check of the container."""

import pytest

pytestmark = pytest.mark.django_db


def test_health_endpoint(client, db):
    response = client.get("/health/", HTTP_ACCEPT="application/json")
    assert response.status_code == 200
