import logging
import os
from datetime import datetime, timezone

from convex import ConvexClient
from flask import Blueprint, current_app, jsonify, request

from digital_converter_webapp.conversion import doJsonConversion
from mireport.filesupport import FilelikeAndFileName
from mireport.JsonToXBRL.mapper import map_json_to_xbrl
from mireport.performance import timed_request, timed_stage
from services.storage_service import GCSStorageService

L = logging.getLogger(__name__)
convex_bp = Blueprint("convex", __name__)

_storage_service: GCSStorageService | None = None


def get_storage_service() -> GCSStorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = GCSStorageService(bucket_name=os.environ["GCS_BUCKET_NAME"])
    return _storage_service


def _parse_reporting_year(raw_value: str | None) -> int:
    value = (raw_value or "").strip()
    if not value:
        return 2025
    try:
        return int(value)
    except ValueError as err:
        raise ValueError("Query parameter reportingYear must be a number.") from err


@convex_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@convex_bp.route("/convex", methods=["GET", "POST"])
def generate_xbrl_from_convex():
    with timed_request():
        return _generate_xbrl_from_convex()


def _generate_xbrl_from_convex():
    org_id = request.args.get("orgId", "").strip()
    reportId = request.args.get("reportId", "").strip()
    convex_url = current_app.config.get("CONVEX_URL") or os.getenv("CONVEX_URL")
    if not convex_url:
        return jsonify({"error": "CONVEX_URL not configured."}), 500

    client = ConvexClient(convex_url)
    if not org_id:
        return jsonify({"error": "Query parameter orgId is required."}), 400
    if not reportId:
        return jsonify({"error": "Query parameter reportId is required."}), 400

    try:
        reporting_year = _parse_reporting_year(request.args.get("reportingYear"))
        
        print(f"\n\nOrg ID: {org_id}, Report ID: {reportId}, Reporting year: {reporting_year}")

        with timed_stage("convex_fetch"):
            convex_data = client.action(
                "report:getCompleteReportData",
                {"orgId": org_id, "reportingYear": reporting_year},
            )
        if not convex_data:
            return jsonify({"error": "No report data found."}), 404
        
        with timed_stage("convex_progress_processing"):
            client.mutation("reportMutations:updateProgress", {"reportId": reportId, "status": "processing"})

        with timed_stage("payload_mapping"):
            mapped_payload = map_json_to_xbrl(convex_data)

        conversion_id = (
            f"xbrl-{org_id}-{reporting_year}-"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        )
        conversion: dict = {"id": conversion_id, "source": "convex"}

        #with timed_stage("conversion"):
        results = doJsonConversion(mapped_payload, conversion, conversion_id)
            
        
        print("\n\n",results.conversionSuccessful,"\n\n", results.toDict(), "\n\n")

        if not results.conversionSuccessful:
            return jsonify(
                {
                    "id": conversion_id,
                    "successful": False,
                    "result": results.toDict(),
                }
            ), 422

        if "zip" not in conversion:
            raise RuntimeError("XBRL ZIP package was not generated.")

        xbrl_package = FilelikeAndFileName.from_tuple(conversion["zip"])
        
        with timed_stage("convex_progress_uploading"):
            client.mutation("reportMutations:updateProgress", {"reportId": reportId, "status": "uploading"})

        object_key = f"reports/{org_id}/{reporting_year}/{conversion_id}.zip"
        with timed_stage("storage_init"):
            storage = get_storage_service()
        with timed_stage("storage_upload"):
            upload_result = storage.upload_bytes(
                file_content=xbrl_package.fileContent,
                destination_blob_name=object_key,
                content_type="application/zip",
            )
        with timed_stage("storage_signed_url"):
            download_url = storage.generate_signed_url(
                object_key=object_key, expiration_minutes=60
            )
            
        returned_Result = {
            **upload_result,
            "downloadUrl": download_url,
        }

        with timed_stage("convex_complete"):
            client.mutation("reportMutations:completeReport", {"reportId": reportId, "storage": returned_Result})
        return jsonify(
            {
                "id": conversion_id,
                "successful": True,
                "reportingYear": reporting_year,
                "storage": upload_result,
                "downloadUrl": download_url,
                "expiresIn": 3600,
                "result": results.toDict(),
            }
        ), 200


    except ValueError as e:
        with timed_stage("convex_progress_failed"):
            client.mutation("reportMutations:updateProgress", {"reportId": reportId, "status": "failed"})
        return jsonify({"error": str(e)}), 400
    except Exception:
        with timed_stage("convex_progress_failed"):
            client.mutation("reportMutations:updateProgress", {"reportId": reportId, "status": "failed"})
        L.exception("Exception during XBRL generation from Convex")
        return jsonify({"error": "Failed to generate XBRL report."}), 500
