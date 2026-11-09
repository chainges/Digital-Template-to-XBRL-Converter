
from mireport import loadBuiltInTaxonomyJSON
from mireport.conversionresults import ConversionResultsBuilder
from mireport.convex_payload_reader import build_report_from_convex_payload

loadBuiltInTaxonomyJSON()


def _build_payload() -> dict:
    return {
        "meta": {
            "entity": {
                "name": "Example Co",
                "identifier": "925446955",
                "identifierScheme": "lei",
            },
            "reportingPeriod": {
                "startDate": "2025-01-01",
                "endDate": "2025-12-31",
            },
            "currency": "EUR",
            "taxonomyEntryPoint": "https://xbrl.efrag.org/taxonomy/vsme/2026-05-01/vsme-all.xsd",
            "reportingLanguage": "en",
        },
        "facts": [],
    }


def test_reader_accepts_dimension_specs_for_pollution_facts() -> None:
    payload = _build_payload()
    payload["facts"] = [
        {
            "concept": "vsme:AmountOfEmissionToAir",
            "value": "123.45",
            "period": "2025-01-01T00:00:00/2025-12-31T00:00:00",
            "dimensions": [
                {
                    "dimension": "vsme:TypeOfPollutantAxis",
                    "member": "vsme:AnthraceneMember",
                }
            ],
        }
    ]

    results = ConversionResultsBuilder("test")
    report = build_report_from_convex_payload(payload, results, {})

    assert report.factCount == 1
    assert results.conversionSuccessful


def test_reader_accepts_enumeration_set_values_from_qnames() -> None:
    payload = _build_payload()
    payload["facts"] = [
        {
            "concept": "vsme:NaceSectorClassificationCodes",
            "value": ["nace:NACE_R8623"],
            "period": "2025-01-01T00:00:00/2025-12-31T00:00:00",
        }
    ]

    results = ConversionResultsBuilder("test")
    report = build_report_from_convex_payload(payload, results, {})

    assert report.factCount == 1
    assert results.conversionSuccessful


def test_reader_accepts_enumeration_single_qname_values() -> None:
    payload = _build_payload()
    payload["facts"] = [
        {
            "concept": "vsme:EmployeeCountingMethodology",
            "value": "vsme:AtTheEndOfTheReportingPeriodMember",
            "period": "2025-01-01T00:00:00/2025-12-31T00:00:00",
        }
    ]

    results = ConversionResultsBuilder("test")
    report = build_report_from_convex_payload(payload, results, {})

    assert report.factCount == 1
    assert results.conversionSuccessful


def test_reader_accepts_legacy_typed_axis_material_dimensions() -> None:
    payload = _build_payload()
    payload["facts"] = [
        {
            "concept": "vsme:NameOfMaterialUsed",
            "value": "steel",
            "period": "2025-01-01T00:00:00/2025-12-31T00:00:00",
            "dimensions": {"vsme:IdentifierOfMaterialTypedAxis": "1"},
        }
    ]

    results = ConversionResultsBuilder("test")
    report = build_report_from_convex_payload(payload, results, {})

    assert report.factCount == 1
    assert results.conversionSuccessful
