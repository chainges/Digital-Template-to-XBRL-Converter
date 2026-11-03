# tc_vsme_to_mapper_adapter.py
"""
Transforms tc-vsme form structure to convex_payload_mapper expected structure.
Maps Norwegian field names to English mapper field names.
"""

def adapt_tc_vsme_to_mapper_format(form_data: dict) -> dict:
    """
    Convert tc-vsme form structure to what build_payload_from_convex_sections expects.
    """
    
    adapted = {}
    
    # Pass through form structure but adapt field names
    if "formGeneral" in form_data:
        adapted["formGeneral"] = {
            "companyInfo": _adapt_company_info(
                form_data.get("formGeneral", {}).get("companyInfo", {})
            ),
            "businessModel": form_data.get("formGeneral", {}).get("businessModel", {}),
            "sustainabilityInitiatives": form_data.get("formGeneral", {}).get("sustainabilityInitiatives", {}),
        }
    
    if "formEnvironmental" in form_data:
        adapted["formEnvironmental"] = {
            "energyEmissions": form_data.get("formEnvironmental", {}).get("energyEmissions", {}),
            "scope3Emissions": form_data.get("formEnvironmental", {}).get("scope3Emissions", {}),
            "waterManagement": form_data.get("formEnvironmental", {}).get("waterManagement", {}),
            "pollution": form_data.get("formEnvironmental", {}).get("pollution", {}),
            "biodiversity": form_data.get("formEnvironmental", {}).get("biodiversity", {}),
            "wasteManagement": _adapt_waste_management(
                form_data.get("formEnvironmental", {}).get("resourceUseCircularEconomy", {})
            ),
        }
    
    if "formSocial" in form_data:
        adapted["formSocial"] = {
            "workforce": _adapt_workforce(
                form_data.get("formSocial", {}).get("workforce", {})
            ),
            "healthSafety": _adapt_health_safety(
                form_data.get("formSocial", {}).get("healthSafety", {})
            ),
            "compensationCollective": form_data.get("formSocial", {}).get("compensationCollective", {}),
            "humanRightsPolicies": form_data.get("formSocial", {}).get("humanRightsPolicies", {}),
        }
    
    if "formGovernance" in form_data:
        adapted["formGovernance"] = {
            "boardComposition": form_data.get("formGovernance", {}).get("boardComposition", {}),
            "finesPenalties": form_data.get("formGovernance", {}).get("finesPenalties", {}),
        }
    
    # Build metadata
    company_info = form_data.get("formGeneral", {}).get("companyInfo", {})
    organization = form_data.get("organization", {})
    
    adapted["meta"] = {
        "entity": {
            "name": company_info.get("organizationName") or organization.get("name"),
            "identifier": company_info.get("organizationNumber") or organization.get("orgNumber"),
            "identifierScheme": "lei",
        }
    }
    
    adapted["reportingYear"] = company_info.get("reportingYear", "2025")
    
    return adapted


def _adapt_company_info(company_info: dict) -> dict:
    """Normalize company info field names."""
    return company_info  # Already has correct English names


def _adapt_workforce(workforce: dict) -> dict:
    """Map Norwegian workforce field names to English."""
    adapted = dict(workforce)
    
    # Map Norwegian field names to English
    if "menn" in adapted:
        adapted["maleEmployees"] = adapted.pop("menn")
    if "kvinner" in adapted:
        adapted["femaleEmployees"] = adapted.pop("kvinner")
    if "annet" in adapted:
        adapted["otherGenderEmployees"] = adapted.pop("annet")
    
    # Total employees calculation
    if "totalEmployees" not in adapted:
        total = 0
        if "heltidsansatte" in adapted:
            total += adapted.get("heltidsansatte", 0)
        if "deltidsansatte" in adapted:
            total += adapted.get("deltidsansatte", 0)
        if "midlertidigAnsatte" in adapted:
            total += adapted.get("midlertidigAnsatte", 0)
        if total > 0:
            adapted["totalEmployees"] = total
    
    if "employeeTurnoverRate" in adapted:
        adapted["turnoverRate"] = adapted.pop("employeeTurnoverRate")
    
    return adapted


def _adapt_health_safety(health_safety: dict) -> dict:
    """Map Norwegian health/safety field names to English."""
    adapted = dict(health_safety)
    
    if "arbeidsulykker" in adapted:
        adapted["workAccidents"] = adapted.pop("arbeidsulykker")
    if "omkomne" in adapted:
        adapted["fatalities"] = adapted.pop("omkomne")
    if "sykefravarProsent" in adapted:
        adapted["sicknesAbsenceRate"] = adapted.pop("sykefravarProsent")
    if "hmsOpplaering" in adapted:
        adapted["healthSafetyTraining"] = adapted.pop("hmsOpplaering")
    
    return adapted


def _adapt_waste_management(circular_economy: dict) -> dict:
    """Map circular economy form to waste management structure."""
    adapted = {
        "totalWaste": circular_economy.get("totalWaste"),
        "hazardousWaste": circular_economy.get("hazardousWaste"),
        "recyclingRate": circular_economy.get("recyclingRate"),
        "applyCircularEconomyPrinciples": circular_economy.get("applyCircularEconomyPrinciples"),
        "circularEconomyDescription": circular_economy.get("circularEconomyDescription"),
    }
    
    # Map waste items if present
    waste_items = []
    if "recycledMaterials" in circular_economy:
        for material in circular_economy.get("recycledMaterials", []):
            waste_items.append({
                "wasteType": material.get("materialType"),
                "divertedAmount": material.get("amount"),
                "unit": material.get("unit"),
            })
    
    if waste_items:
        adapted["wasteItems"] = waste_items
    
    return adapted