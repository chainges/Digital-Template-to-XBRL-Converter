import logging
from typing import Any

from flask import current_app

from mireport.arelle.report_info import (
    ARELLE_VERSION_INFORMATION,
    ArelleReportProcessor,
)
from mireport.convex_payload_reader import build_report_from_convex_payload
from mireport.conversionresults import (
    ConversionResults,
    ConversionResultsBuilder,
    MessageType,
    Severity,
)
from mireport.data.disclosures import VSME_DEFAULTS

L = logging.getLogger(__name__)


def getArelle() -> ArelleReportProcessor:
    return ArelleReportProcessor(
        taxonomyPackages=current_app.config["TAXONOMY_PACKAGES"],
        workOffline=current_app.config["ARELLE_WORK_OFFLINE"],
    )


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def doJsonConversion(payload: dict, conversion: dict, id: str) -> ConversionResults:
    """Convert a mapped JSON payload to an Inline XBRL report package.

    The generated package is stored in ``conversion["zip"]``.
    """
    resultBuilder = ConversionResultsBuilder(conversionId=id)

    try:
        with resultBuilder.processingContext(f"JSON Conversion {id}") as pc:
            pc.mark("Extracting data from JSON payload")

            report = build_report_from_convex_payload(
                payload, resultBuilder, VSME_DEFAULTS
            )
            if not report.hasFacts:
                resultBuilder.addMessage(
                    "No facts found in payload-derived report. Stopping here.",
                    Severity.ERROR,
                    MessageType.Conversion,
                )
                return resultBuilder.build()

            pc.mark(
                "Generating Inline Report",
                additionalInfo=f"({report.factCount} facts to include)",
            )
            report_package = report.getInlineReportPackage()
            conversion["zip"] = report_package
            resultBuilder.addMessage(
                f"Inline XBRL report {report_package} created (containing {report.factCount} facts)",
                Severity.INFO,
                MessageType.Conversion,
            )

            options = payload.get("options", {})
            if not isinstance(options, dict):
                options = {}

            validate = _as_bool(options.get("validate"), True)
            generate_viewer = _as_bool(options.get("generateViewer"), False)
            generate_xbrl_json = _as_bool(options.get("generateXbrlJson"), False)

            if validate:
                pc.mark(
                    "Validating Inline Report",
                    additionalInfo=f"Using Arelle (XBRL Certified Software™) [{ARELLE_VERSION_INFORMATION}]",
                )
                arelle_results = getArelle().validateReportPackage(report_package)
                resultBuilder.addMessages(arelle_results.messages)

            if generate_viewer:
                pc.mark("Generating Inline Viewer")
                viewer_results = getArelle().generateInlineViewer(report_package)
                resultBuilder.addMessages(viewer_results.messages)
                if viewer_results.has_viewer:
                    conversion["viewer"] = viewer_results.viewer

            if generate_xbrl_json:
                pc.mark("Generating XBRL-JSON")
                json_results = getArelle().generateXBRLJson(report_package)
                resultBuilder.addMessages(json_results.messages)
                if json_results.has_json:
                    conversion["json"] = json_results.xBRL_JSON
    except Exception as e:
        message = next(iter(e.args), str(e))
        resultBuilder.addMessage(
            f"Exception encountered during JSON conversion. {message}",
            Severity.ERROR,
            MessageType.Conversion,
        )
        L.exception("Exception encountered during JSON conversion", exc_info=e)

    return resultBuilder.build()
