from mireport.JsonToXBRL import map_json_to_xbrl


def test_modular_mapper_returns_payload_skeleton():
    result = map_json_to_xbrl(
        {
            "formGeneral": {
                "companyInfo": {
                    "organizationName": "Example Ltd",
                    "organizationNumber": "123456",
                    "reportingYear": "2024",
                    "currency": "EUR",
                }
            }
        }
    )

    assert result["meta"]["entity"]["name"] == "Example Ltd"
    assert result["meta"]["entity"]["identifier"] == "123456"
    assert result["meta"]["reportingPeriod"] == {
        "startDate": "2024-01-01",
        "endDate": "2024-12-31",
    }
    assert result["facts"] == []
    assert result["warnings"] == []
    assert result["factCount"] == 0