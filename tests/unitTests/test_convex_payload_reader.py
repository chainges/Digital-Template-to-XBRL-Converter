import json

from mireport import loadBuiltInTaxonomyJSON
from mireport.conversionresults import ConversionResultsBuilder
from mireport.convex_payload_mapper import VSMEMapper, map_json_to_xbrl
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


def test_mapper_emits_dimension_specs_for_pollution_facts() -> None:
    payload = {
        "formGeneral": {
            "companyInfo": {
                "organizationName": "Example Co",
                "organizationNumber": "925446955",
                "reportingYear": "2025",
            }
        },
        "formEnvironmental": {
            "pollution": {
                "reportingPollution": True,
                "pollutants": [
                    {
                        "pollutantCode": "Anthracene",
                        "amountOfEmissionToAir": 1234,
                        "amountOfEmissionToWater": 0,
                        "amountOfEmissionToSoil": 0,
                        "unitCode": "kg",
                    }
                ],
            }
        },
        "formSocial": {},
        "formGovernance": {},
        "organization": {"name": "Example Co", "orgNumber": "925446955"},
    }

    mapped = map_json_to_xbrl(payload)
    pollution_fact = next(
        fact for fact in mapped["facts"] if fact["concept"] == "vsme:AmountOfEmissionToAir"
    )

    dimensions = pollution_fact["dimensions"]

    assert dimensions
    if isinstance(dimensions, list):
        dimension_spec = dimensions[0]
    else:
        dimension_spec = dimensions

    assert dimension_spec["dimension"] == "vsme:TypeOfPollutantAxis"
    assert dimension_spec["member"] == "vsme:AnthraceneMember"


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


def test_mapper_emits_enumeration_set_values_as_member_lists() -> None:
    payload = {
        "formGeneral": {
            "companyInfo": {
                "organizationName": "Example Co",
                "organizationNumber": "925446955",
                "reportingYear": "2025",
            }
        },
        "formEnvironmental": {},
        "formSocial": {
            "humanRightsPolicies": {
                "hasCodeOfConduct": True,
                "childLaborPolicy": True,
                "discriminationPolicy": True,
                "forcedLaborPolicy": True,
                "humanTraffickingPolicy": True,
                "accidentPreventionPolicy": True,
            }
        },
        "formGovernance": {},
        "organization": {"name": "Example Co", "orgNumber": "925446955"},
    }

    mapped = map_json_to_xbrl(payload)
    fact = next(
        fact
        for fact in mapped["facts"]
        if fact["concept"] == "vsme:TypeOfContentCoveredByTheCodeOfConductOrHumanRightsPolicyForItsOwnWorkforce"
    )

    assert fact["value"] == [
        "vsme:AccidentPreventionMember",
        "vsme:ChildLabourMember",
        "vsme:DiscriminationMember",
        "vsme:ForcedLabourMember",
        "vsme:HumanTraffickingMember",
    ]


def test_mapper_preserves_dynamic_sustainability_initiatives() -> None:
    payload = {
        "formGeneral": {
            "companyInfo": {
                "organizationName": "Example Co",
                "organizationNumber": "925446955",
                "reportingYear": "2025",
                "sustainabilityInitiatives": [
                    "ClimateChangeMember",
                    "WaterMember",
                    "Water reuse program at the main facility",
                ],
            }
        },
        "formEnvironmental": {},
        "formSocial": {},
        "formGovernance": {},
        "organization": {"name": "Example Co", "orgNumber": "925446955"},
    }

    mapper = VSMEMapper(payload)
    mapper.map_company_info()
    mapped = {"facts": mapper.builder.get_facts()}
    issue_fact = next(
        fact
        for fact in mapped["facts"]
        if fact["concept"]
        == "vsme:SustainabilityIssueAddressedByPracticePolicyAndOrFutureInitiative"
    )
    description_fact = next(
        fact
        for fact in mapped["facts"]
        if fact["concept"]
        == "vsme:DescriptionOfPracticesPoliciesAndOrFutureInitiatives"
    )

    assert issue_fact["value"] == [
        "vsme:ClimateChangeMember",
        "vsme:WaterAndMarineResourcesMember",
    ]
    assert description_fact["value"] == "Water reuse program at the main facility"


def test_mapper_handles_missing_sustainability_initiative_description() -> None:
    payload = {
        "formGeneral": {
            "companyInfo": {
                "organizationName": "Example Co",
                "organizationNumber": "925446955",
                "reportingYear": "2025",
            },
            "sustainabilityInitiatives": {
                "initiatives": ["ClimateChangeMember", "WaterMember"],
                "hasSetTargets": True,
                "isPubliclyAvailable": True,
            },
        },
        "formEnvironmental": {},
        "formSocial": {},
        "formGovernance": {},
        "organization": {"name": "Example Co", "orgNumber": "925446955"},
    }

    mapper = VSMEMapper(payload)
    mapper.map_company_info()
    mapped = {"facts": mapper.builder.get_facts()}

    issue_fact = next(
        fact
        for fact in mapped["facts"]
        if fact["concept"] == "vsme:SustainabilityIssueAddressedByPracticePolicyAndOrFutureInitiative"
    )
    assert issue_fact["value"] == ["vsme:ClimateChangeMember", "vsme:WaterAndMarineResourcesMember"]

    description_fact = next(
        (
            fact
            for fact in mapped["facts"]
            if fact["concept"] == "vsme:DescriptionOfPracticesPoliciesAndOrFutureInitiatives"
        ),
        None,
    )
    assert description_fact is None


def test_mapper_emits_typed_dimension_specs_for_material_facts() -> None:
    payload = {
        "formGeneral": {
            "companyInfo": {
                "organizationName": "Example Co",
                "organizationNumber": "925446955",
                "reportingYear": "2025",
            }
        },
        "formEnvironmental": {
            "resourceUseCircularEconomy": {
                "annualMassFlows": [
                    {
                        "materialType": "steel",
                        "unit": "kg",
                        "volume": 2300000,
                    }
                ]
            }
        },
        "formSocial": {},
        "formGovernance": {},
        "organization": {"name": "Example Co", "orgNumber": "925446955"},
    }

    mapped = map_json_to_xbrl(payload)
    material_fact = next(
        fact for fact in mapped["facts"] if fact["concept"] == "vsme:NameOfMaterialUsed"
    )

    dimensions = material_fact["dimensions"]
    assert dimensions["dimension"] == "vsme:IdentifierOfMaterialTypedAxis"
    assert dimensions["typedValue"] == 1


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
