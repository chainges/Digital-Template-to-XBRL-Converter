import logging
from unittest.mock import MagicMock

import pytest

from digital_converter_webapp import conversion as web_conversion
from digital_converter_webapp import create_app
from digital_converter_webapp.routes import convex_routes
from mireport.arelle.report_info import BIG_ARELLE_LOCK, _timed_arelle_lock
from mireport.filesupport import FilelikeAndFileName


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CONVEX_URL", "https://example.convex.cloud")
    app = create_app({"TESTING": True})
    return app.test_client()


def test_health(client) -> None:
    assert client.get("/health").status_code == 200


def test_missing_org_id(client) -> None:
    assert client.get("/convex").status_code == 400


def test_invalid_reporting_year(client, monkeypatch) -> None:
    monkeypatch.setattr(convex_routes, "ConvexClient", MagicMock())
    assert client.get("/convex?orgId=a&reportId=r&reportingYear=abc").status_code == 400


def test_no_data(client, monkeypatch) -> None:
    fake = MagicMock()
    fake.return_value.action.return_value = None
    monkeypatch.setattr(convex_routes, "ConvexClient", fake)
    assert client.get("/convex?orgId=a&reportId=r").status_code == 404


def test_conversion_failure_returns_422(client, monkeypatch) -> None:
    fake = MagicMock()
    fake.return_value.action.return_value = {"formGeneral": {}}
    monkeypatch.setattr(convex_routes, "ConvexClient", fake)
    monkeypatch.setattr(convex_routes, "map_json_to_xbrl", lambda d: {"facts": []})
    results = MagicMock(conversionSuccessful=False)
    results.toDict.return_value = {}
    monkeypatch.setattr(convex_routes, "doJsonConversion", lambda *a: results)
    assert client.get("/convex?orgId=a&reportId=r").status_code == 422


def test_successful_request_logs_correlated_stage_timings(client, monkeypatch, caplog):
    fake = MagicMock()
    fake.return_value.action.return_value = {"formGeneral": {}}
    monkeypatch.setattr(convex_routes, "ConvexClient", fake)
    monkeypatch.setattr(convex_routes, "map_json_to_xbrl", lambda data: {"facts": []})

    def convert(payload, conversion, conversion_id):
        conversion["zip"] = (b"package", "report.zip")
        results = MagicMock(conversionSuccessful=True)
        results.toDict.return_value = {}
        return results

    monkeypatch.setattr(convex_routes, "doJsonConversion", convert)
    storage = MagicMock()
    storage.upload_bytes.return_value = {"objectKey": "example"}
    storage.generate_signed_url.return_value = "https://example.com/report"
    monkeypatch.setattr(convex_routes, "get_storage_service", lambda: storage)

    with caplog.at_level(logging.INFO, logger="mireport.performance"):
        response = client.get("/convex?orgId=secret-org&reportId=secret-report")

    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records if record.name == "mireport.performance"]
    stages = {message.split("stage=")[1].split()[0] for message in messages}
    assert stages == {
        "convex_fetch", "convex_progress_processing", "payload_mapping", "conversion",
        "convex_progress_uploading", "storage_init", "storage_upload", "storage_signed_url",
        "convex_complete", "request_total",
    }
    request_ids = {message.split("request_id=")[1].split()[0] for message in messages}
    assert len(request_ids) == 1
    assert "-" not in request_ids
    assert all("secret-org" not in message and "secret-report" not in message for message in messages)


def test_failed_request_logs_failed_stage_and_total(client, monkeypatch, caplog):
    fake = MagicMock()
    fake.return_value.action.side_effect = RuntimeError("network failure")
    monkeypatch.setattr(convex_routes, "ConvexClient", fake)

    with caplog.at_level(logging.INFO, logger="mireport.performance"):
        response = client.get("/convex?orgId=a&reportId=r")

    assert response.status_code == 500
    messages = [record.getMessage() for record in caplog.records if record.name == "mireport.performance"]
    assert any("stage=convex_fetch " in message for message in messages)
    assert any("stage=request_total " in message for message in messages)


def test_conversion_validates_by_default(client, monkeypatch, caplog):
    package = FilelikeAndFileName(b"package", "report.zip")
    report = MagicMock(hasFacts=True, factCount=1)
    report.getInlineReportPackage.return_value = package
    processor = MagicMock()
    processor.validateReportPackage.return_value.messages = []
    monkeypatch.setattr(web_conversion, "build_report_from_convex_payload", lambda *args: report)
    monkeypatch.setattr(web_conversion, "getArelle", lambda: processor)

    with client.application.app_context(), caplog.at_level(logging.INFO, logger="mireport.performance"):
        conversion = {}
        results = web_conversion.doJsonConversion({}, conversion, "test")

    assert results.conversionSuccessful
    assert conversion["zip"] == package
    processor.validateReportPackage.assert_called_once_with(package)
    assert any("stage=validation " in record.getMessage() for record in caplog.records)


def test_arelle_lock_is_released_and_timed_on_error(caplog):
    with caplog.at_level(logging.INFO, logger="mireport.performance"), pytest.raises(RuntimeError):
        with _timed_arelle_lock():
            assert BIG_ARELLE_LOCK.locked()
            raise RuntimeError("test")

    assert not BIG_ARELLE_LOCK.locked()
    messages = [record.getMessage() for record in caplog.records]
    assert any("stage=arelle_lock_wait " in message for message in messages)
    assert any("stage=arelle_execution " in message for message in messages)
