"""Top-level orchestration for the modular JSON-to-XBRL mapper."""

import logging
from typing import Any, Dict, Optional

from .common import XBRLFactBuilder
from .common import ConfidentialAreas
from .environmental import EnvironmentalMapper
from .general_information import GeneralInformationMapper
from .governance import GovernanceMapper
from .social import SocialMapper

logger = logging.getLogger(__name__)


class VSMEMapper:
    """Coordinate section mappers and assemble the standard payload."""

    def __init__(self, json_data: Dict[str, Any]):
        self.data = json_data
        self.form_general = json_data.get("formGeneral", {})
        company_info = self.form_general.get("companyInfo", {})

        self.entity_id = (
            company_info.get("organizationNumber")
        )
        reporting_year = company_info.get("reportingYear") or "2025"
        self.period_start = f"{reporting_year}-01-01"
        self.period_end = f"{reporting_year}-12-31"
        
        self.builder = XBRLFactBuilder(
            self.entity_id,
            self.period_start,
            self.period_end,
        )

        self.general_information = GeneralInformationMapper(json_data, self.builder)
        #self.confidential_areas = ConfidentialAreas(json_data.get("confidentialAreas", []))
        self.environmental = EnvironmentalMapper(json_data, self.builder)
        self.social = SocialMapper(json_data, self.builder)
        self.governance = GovernanceMapper(json_data, self.builder)

    def map_all(self) -> Dict[str, Any]:
        """Run each section mapper and return the converter payload shape."""
        logger.info("Starting modular mapper for entity %s", self.entity_id)
        self.general_information.map_all()
        self.environmental.map_all()
        self.social.map_all()
        self.governance.map_all()

        company_info = self.form_general.get("companyInfo", {})
        facts = self.builder.get_facts()
        return {
            "meta": {
                "entity": {
                    "name": company_info.get("organizationName")
                    or company_info.get("organizationName"),
                    "identifier": self.entity_id,
                    "identifierScheme": "lei",
                },
                "reportTitle": "Sustainability Report",
                "reportSubtitle": (
                    "Prepared in accordance with the EFRAG Voluntary Sustainability "
                    "Reporting Standard for Non-Listed SMEs (VSME)."
                ),
                "reportingPeriod": {
                    "startDate": self.period_start,
                    "endDate": self.period_end,
                },
                "currency": company_info.get("currency", "EUR"),
                "taxonomyEntryPoint": (
                    "https://xbrl.efrag.org/taxonomy/vsme/2026-05-01/vsme-all.xsd"
                ),
                "reportingLanguage": "en",
                "namespaces": {
                    "vsme": "https://xbrl.efrag.org/taxonomy/vsme/2026-05-01/vsme",
                    "nace": "https://xbrl.efrag.org/taxonomy/nace/2026-05-01",
                    "country": "https://xbrl.org/2024/iso3166",
                    "enum2": "http://xbrl.org/2020/extensible-enumerations-2.0",
                },
            },
            "facts": facts,
            "warnings": self.builder.get_errors(),
            "factCount": len(facts),
        }


def map_json_to_xbrl(
    json_data: Dict[str, Any], defaults: Optional[Any] = None
) -> Dict[str, Any]:
    """Map input JSON using the modular section mapper scaffold."""
    del defaults
    return VSMEMapper(json_data).map_all()