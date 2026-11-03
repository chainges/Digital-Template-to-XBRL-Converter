from convex import ConvexClient
from datetime import datetime, timezone

from flask import Blueprint, request, make_response, jsonify, current_app, session, url_for

#from digital_converter_webapp import doJsonConversion
from mireport.JsonToXBRL.mapper import map_json_to_xbrl
#from mireport.convex_payload_mapper import map_json_to_xbrl
from mireport.xlsx_template_reader.processor import VSME_DEFAULTS
from mireport.filesupport import FilelikeAndFileName

import logging
import os
from typing import Any
from mireport.tc_vsme_to_mapper_adapter import adapt_tc_vsme_to_mapper_format
from pathlib import Path
import json
import os

from services.storage_service import GCSStorageService

_storage_service = None

def get_storage_service() -> GCSStorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = GCSStorageService(bucket_name=os.environ["GCS_BUCKET_NAME"])
    return _storage_service
#from digital_converter_webapp import doJsonConversion

L = logging.getLogger(__name__)
convex_bp = Blueprint("convex", __name__)

def _parse_reporting_year(raw_value: str | None) -> int:
    """Parse and validate reporting year."""
    value = (raw_value or "").strip()
    if not value:
        return 2025
    try:
        return int(value)
    except ValueError as err:
        raise ValueError("Query parameter reportingYear must be a number.") from err

# ============================================================================
# ROUTE 1: /convex - Returns mapped VSME JSON only (no XBRL conversion)
# ============================================================================


@convex_bp.route("/convex", methods=["GET", "POST"])
def generate_xbrl_from_convex():
    from digital_converter_webapp import doJsonConversion

    org_id = request.args.get("orgId", "").strip()

    if not org_id:
        return jsonify({
            "error": "Query parameter orgId is required."
        }), 400

    reporting_year = _parse_reporting_year(
        request.args.get("reportingYear")
    )

    try:
        # Step 1: Get Convex configuration
        convex_url = (
            current_app.config.get("CONVEX_URL")
            or os.getenv("CONVEX_URL")
        )

        if not convex_url:
            return jsonify({
                "error": "CONVEX_URL not configured."
            }), 500

        # Step 2: Fetch complete report data
        client = ConvexClient(convex_url)

        convex_data = client.action(
            "report:getCompleteReportData",
            {
                "orgId": org_id,
                "reportingYear": reporting_year
            }
        )

        if not convex_data:
            return jsonify({
                "error": "No report data found."
            }), 404

        # Step 3: Map data to VSME taxonomy
        mapped_payload = map_json_to_xbrl(
            convex_data,
            VSME_DEFAULTS
        )

        # Step 4: Generate XBRL
        conversion_id = (
            f"xbrl-{org_id}-{reporting_year}-"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        )

        conversion = {
            "id": conversion_id,
            "source": "convex"
        }

        results = doJsonConversion(
            mapped_payload,
            conversion,
            conversion_id
        )
        
        print("\n\nConversion Results:\n",results.toDict())

        if not results.conversionSuccessful:
            return jsonify({
                "id": conversion_id,
                "successful": False,
                "result": results.toDict()
            }), 422

        # Step 5: Get generated ZIP
        if "zip" not in conversion:
            raise ValueError(
                "XBRL ZIP package was not generated."
            )

        xbrl_package = FilelikeAndFileName.from_tuple(
            conversion["zip"]
        )

        # Step 6: Upload directly to GCS
        filename = f"{conversion_id}.zip"

        object_key = (
            f"reports/{org_id}/{reporting_year}/{filename}"
        )

        upload_result = get_storage_service().upload_bytes(
            file_content=xbrl_package.fileContent,
            destination_blob_name=object_key,
            content_type="application/zip"
        )

        # Step 7: Generate signed download URL
        download_url = get_storage_service().generate_signed_url(
            object_key=object_key,
            expiration_minutes=60
        )

        # Step 8: Return response
        return jsonify({
            "id": conversion_id,
            "successful": True,
            "reportingYear": reporting_year,
            "storage": upload_result,
            "downloadUrl": download_url,
            "expiresIn": 3600,
            "result": results.toDict()
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    except Exception:
        L.exception("Exception during XBRL generation from Convex")

        return jsonify({
            "error": "Failed to generate XBRL report."
        }), 500


# ============================================================================
# ROUTE 2: /xbrl - Full pipeline: Convex → VSME → XBRL conversion
# ============================================================================

def _parse_reporting_year(raw_value: str | None) -> int:
    """Parse and validate reporting year."""
    value = (raw_value or "").strip()
    if not value:
        return 2025
    try:
        return int(value)
    except ValueError as err:
        raise ValueError("Query parameter reportingYear must be a number.") from err

@convex_bp.route("/xbrl-from-test-file", methods=["GET"])
def generate_xbrl_from_test_file() -> tuple[dict, int]:
    """
    GET /xbrl-from-test-file
    Reads TestFile.json from root, converts to XBRL
    """
    from digital_converter_webapp import doJsonConversion
    
    try:
        # Read test file
        test_file_path = Path("TestFile.json")
        if not test_file_path.exists():
            return {"error": f"TestFile.json not found at {test_file_path.absolute()}"}, 404
        
        with open(test_file_path, "r") as f:
            data = json.load(f)

        mapped_payload = map_json_to_xbrl(data)

        with open("mapped_payload.json", "w") as f:
            json.dump(mapped_payload, f, indent=2)
        
        # Convert to XBRL
        conversion_id = f"xbrl-test-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        conversion = {"id": conversion_id, "source": "test-file"}
        
        results = doJsonConversion(mapped_payload, conversion, conversion_id)
        

        # Save output
        output_dir = Path("reports/xbrl")
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"test_{conversion_id}.zip"
        file_path = output_dir / filename
        
        if "zip" in conversion:
            xbrl_package = FilelikeAndFileName.from_tuple(conversion["zip"])
            with open(file_path, "wb") as f:
                f.write(xbrl_package.fileContent)
        
        status_code = 200 if results.conversionSuccessful else 422
        return jsonify({
            "id": conversion_id,
            "successful": results.conversionSuccessful,
            "file": str(file_path),
            "result": results.toDict()
        }), status_code
        
    except Exception as e:
        L.exception("Test file XBRL conversion failed", exc_info=e)
        return {"error": str(e)}, 500

@convex_bp.route("/xbrl", methods=["GET"])
def generate_xbrl_report() -> tuple[dict, int]:
    """
    GET /xbrl?orgId=abc&reportingYear=2024
    
    Converts Convex data → VSME → XBRL
    Saves XBRL file locally and returns file path
    """

    from .. import doJsonConversion

    org_id = request.args.get("orgId", "").strip()
    if not org_id:
        return {"error": "Query parameter orgId is required."}, 400
    
    reporting_year = _parse_reporting_year(request.args.get("reportingYear"))
    
    try:
        convex_url = current_app.config.get("CONVEX_URL") or os.getenv("CONVEX_URL")
        if not convex_url:
            return {"error": "CONVEX_URL not configured in environment"}, 500
        
        # Step 1: Get Convex data
        client = ConvexClient(convex_url)
        convex_data = client.action(
            "report:getCompleteReportData",
            {"orgId": org_id, "reportingYear": reporting_year}
        )

        adapted_data = adapt_tc_vsme_to_mapper_format(convex_data)

        import json
        L.info("=== ADAPTED DATA ===")
        L.info(f"formGeneral.companyInfo: {json.dumps(adapted_data.get('formGeneral', {}).get('companyInfo', {}), default=str)}")
        L.info(f"formGeneral keys: {list(adapted_data.get('formGeneral', {}).keys())}")
        L.info(f"formEnvironmental.pollution: {json.dumps(adapted_data.get('formEnvironmental', {}).get('pollution', {}), default=str)}")
        L.info(f"formSocial.workforce: {json.dumps(adapted_data.get('formSocial', {}).get('workforce', {}), default=str)}")
        
        # Step 3: Map to VSME
        mapped_payload = map_json_to_xbrl(adapted_data)
        
        # DEBUG: What came out?
        L.info("=== MAPPED PAYLOAD RESULT ===")
        facts = mapped_payload.get('facts', [])
        L.info(f"Total facts generated: {len(facts)}")
        L.info(f"Meta: {json.dumps(mapped_payload.get('meta', {}), default=str)}")
        if facts:
            L.info(f"First fact: {json.dumps(facts[0], default=str)}")
        else:
            L.critical("ZERO FACTS - MAPPING FAILED")
        
        # Step 2: Map to VSME
        mapped_payload = map_json_to_xbrl(adapted_data, VSME_DEFAULTS)
        
        # Step 3: Convert to XBRL
        conversion_id = f"xbrl-{org_id}-{reporting_year}"
        conversion = session.setdefault(conversion_id, {"id": conversion_id})
        conversion["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conversion["source"] = "convex-xbrl"
        conversion["orgId"] = org_id
        
        # Run XBRL conversion
        results = doJsonConversion(mapped_payload, conversion, conversion_id)
        conversion["results"] = results.toDict()
        conversion["successful"] = results.conversionSuccessful
        
        # Step 4: Save XBRL file locally
        output_dir = Path("reports/xbrl")  # Create reports/xbrl directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{org_id}_{reporting_year}_{timestamp}.zip"
        file_path = output_dir / filename
        
        # Extract and save XBRL zip file
        if "zip" in conversion:
            xbrl_package = FilelikeAndFileName.from_tuple(conversion["zip"])
            with open(file_path, "wb") as f:
                f.write(xbrl_package.fileContent)
            
            L.info(f"XBRL report saved to: {file_path}")
        else:
            return {
                "error": "XBRL generation failed - no zip file produced",
                "details": results.toDict()
            }, 422
        
        # Step 5: Return result with file path
        body: dict[str, Any] = {
            "id": conversion_id,
            "successful": results.conversionSuccessful,
            "orgId": org_id,
            "reportingYear": reporting_year,
            "timestamp": conversion["date"],
            "file": {
                "path": str(file_path),
                "filename": filename,
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
            },
            "result": results.toDict(),
            "links": {
                "conversion": url_for("basic.convert", id=conversion_id),
                "download_zip": url_for("basic.downloadFile", id=conversion_id, ftype="zip"),
                "viewer": url_for("basic.viewer", id=conversion_id),
            },
        }
        
        status_code = 200 if results.conversionSuccessful else 422
        return make_response(jsonify(body), status_code)
        
    except ValueError as e:
        return {"error": str(e)}, 400
    except Exception as e:
        L.exception("Exception during XBRL conversion", exc_info=e)
        return {"error": "Failed to generate XBRL report.", "details": str(e)}, 500
        
    except ValueError as e:
        return {"error": str(e)}, 400
    except Exception as e:
        L.exception("Exception during XBRL conversion", exc_info=e)
        return {"error": "Failed to generate XBRL report."}, 500