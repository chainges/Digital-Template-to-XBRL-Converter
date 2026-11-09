import logging
from collections.abc import Mapping
from typing import Any

from dotenv import load_dotenv
from flask import Flask

from mireport import loadBuiltInTaxonomyJSON
from mireport.arelle.report_info import ArelleReportProcessor

from .routes.convex_routes import convex_bp

L = logging.getLogger(__name__)


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    load_dotenv()

    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="[%Y-%m-%d %H:%M:%S]",
        level=logging.INFO,
    )
    logging.captureWarnings(True)

    loadBuiltInTaxonomyJSON()

    app = Flask(__name__, static_folder=None)
    app.config.from_prefixed_env()
    if test_config:
        app.config.update(test_config)

    app.register_blueprint(convex_bp, url_prefix=app.config.get("PREFIX", "/"))

    # Discover taxonomy packages up front so Arelle can validate offline.
    taxonomyPackageList = ArelleReportProcessor.getTaxonomyPackagesFromDir(
        app.config.get("TAXONOMY_PACKAGE_DIR")
    )
    app.config["TAXONOMY_PACKAGES"] = taxonomyPackageList
    app.config["ARELLE_WORK_OFFLINE"] = app.config.get(
        "ARELLE_WORK_OFFLINE", bool(taxonomyPackageList)
    )

    return app
