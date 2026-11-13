import argparse
import json
import math
import platform
import statistics
import sys
import time
from contextlib import redirect_stdout
from importlib.metadata import version
from pathlib import Path

from mireport import loadBuiltInTaxonomyJSON
from mireport.arelle.report_info import ArelleReportProcessor
from mireport.conversionresults import ConversionResultsBuilder, Severity
from mireport.convex_payload_reader import build_report_from_convex_payload
from mireport.data.disclosures import VSME_DEFAULTS
from mireport.JsonToXBRL.mapper import map_json_to_xbrl


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark local report generation.")
    parser.add_argument("payload", type=Path, help="Path to a Convex JSON payload.")
    parser.add_argument("--iterations", type=int, default=10, help="Warm iterations.")
    parser.add_argument("--validate", action="store_true", help="Include Arelle validation.")
    parser.add_argument("--taxonomy-package-dir", type=Path, help="Local taxonomy packages for offline validation.")
    parser.add_argument("--online", action="store_true", help="Allow online taxonomy resolution during validation.")
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be at least 1")
    if args.validate and not args.online and not args.taxonomy_package_dir:
        parser.error("offline validation requires --taxonomy-package-dir; alternatively pass --online")

    packages = ArelleReportProcessor.getTaxonomyPackagesFromDir(args.taxonomy_package_dir)
    if args.validate and not args.online and not packages:
        parser.error("no taxonomy packages found in --taxonomy-package-dir")
    processor = ArelleReportProcessor(taxonomyPackages=packages, workOffline=not args.online)
    source = json.loads(args.payload.read_text(encoding="utf-8"))

    start = time.perf_counter()
    with redirect_stdout(sys.stderr):
        loadBuiltInTaxonomyJSON()
    taxonomy_seconds = time.perf_counter() - start

    def run() -> dict:
        start = time.perf_counter()
        cpu_start = time.process_time()
        mapped = map_json_to_xbrl(source)
        mapped_at = time.perf_counter()
        builder = ConversionResultsBuilder("benchmark")
        report = build_report_from_convex_payload(mapped, builder, VSME_DEFAULTS)
        if not report.hasFacts or not builder.conversionSuccessful:
            raise RuntimeError("Benchmark input did not produce a successful report with facts")
        built_at = time.perf_counter()
        package = report.getInlineReportPackage()
        packaged_at = time.perf_counter()
        errors = None
        if args.validate:
            result = processor.validateReportPackage(package)
            errors = sum(message.severity == Severity.ERROR for message in result.messages)
        finished = time.perf_counter()
        return {
            "mapping_seconds": mapped_at - start,
            "build_seconds": built_at - mapped_at,
            "package_seconds": packaged_at - built_at,
            "validation_seconds": finished - packaged_at if args.validate else None,
            "total_seconds": finished - start,
            "cpu_seconds": time.process_time() - cpu_start,
            "fact_count": report.factCount,
            "package_bytes": len(package.fileContent),
            "validation_errors": errors,
        }

    with redirect_stdout(sys.stderr):
        cold = run()
        warm = [run() for _ in range(args.iterations)]
    totals = sorted(sample["total_seconds"] for sample in warm)
    print(json.dumps({
        "python": platform.python_version(),
        "arelle": version("arelle-release"),
        "validated": args.validate,
        "online": args.online if args.validate else None,
        "taxonomy_package_count": len(packages),
        "taxonomy_startup_seconds": taxonomy_seconds,
        "cold": cold,
        "warm_iterations": len(warm),
        "warm_median_seconds": statistics.median(totals),
        "warm_p95_seconds": totals[math.ceil(0.95 * len(totals)) - 1],
        "warm_runs": warm,
    }, indent=2))


if __name__ == "__main__":
    main()