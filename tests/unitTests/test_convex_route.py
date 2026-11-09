from unittest.mock import MagicMock

import pytest

from digital_converter_webapp import create_app
from digital_converter_webapp.routes import convex_routes


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CONVEX_URL", "https://example.convex.cloud")
    app = create_app({"TESTING": True})
    return app.test_client()


def test_health(client) -> None:
    assert client.get("/health").status_code == 200


def test_missing_org_id(client) -> None:
    assert client.get("/convex").status_code == 400


def test_invalid_reporting_year(client) -> None:
    assert client.get("/convex?orgId=a&reportingYear=abc").status_code == 400


def test_no_data(client, monkeypatch) -> None:
    fake = MagicMock()
    fake.return_value.action.return_value = None
    monkeypatch.setattr(convex_routes, "ConvexClient", fake)
    assert client.get("/convex?orgId=a").status_code == 404


def test_conversion_failure_returns_422(client, monkeypatch) -> None:
    fake = MagicMock()
    fake.return_value.action.return_value = {"formGeneral": {}}
    monkeypatch.setattr(convex_routes, "ConvexClient", fake)
    monkeypatch.setattr(convex_routes, "map_json_to_xbrl", lambda d: {"facts": []})
    results = MagicMock(conversionSuccessful=False)
    results.toDict.return_value = {}
    monkeypatch.setattr(convex_routes, "doJsonConversion", lambda *a: results)
    assert client.get("/convex?orgId=a").status_code == 422
