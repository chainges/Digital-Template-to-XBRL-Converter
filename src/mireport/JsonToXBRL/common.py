"""Shared utilities for the modular JSON-to-XBRL mappers."""

from enum import Enum
from typing import Any, Dict, List, Optional


class ConfidentialAreas:
	def __init__(self, areas: List[str]):
		self.areas = areas

	def __contains__(self, area: str) -> bool:
		return area in self.areas

class EFRAGTaxonomy:
    """EFRAG VSME Taxonomy constants"""

    SUSTAINABILITY_ISSUE_MEMBERS = {
        "climatechangemember": "vsme:ClimateChangeMember",
        "pollutionmember": "vsme:PollutionMember",
        "watermember": "vsme:WaterAndMarineResourcesMember",
        "waterandmarineresourcesmember": "vsme:WaterAndMarineResourcesMember",
        "biodiversitymember": "vsme:BiodiversityAndEcosystemsMember",
        "biodiversityandecosystemsmember": "vsme:BiodiversityAndEcosystemsMember",
        "circulareconomymember": "vsme:CircularEconomyMember",
        "ownworkforcemember": "vsme:OwnWorkforceMember",
        "workersinthevaluechainmember": "vsme:WorkersInTheValueChainMember",
        "affectedcommunitiesmember": "vsme:AffectedCommunitiesMember",
        "consumersandendusersmember": "vsme:ConsumersAndEndUsersMember",
        "businessconductmember": "vsme:BusinessConductMember",
    }
    
    # Scope 3 Categories (GHG Protocol) taxonomy explicit dimension members
    SCOPE3_CATEGORY_MEMBERS = {
        "category1": "vsme:PurchasedGoodsAndServicesMember",
        "category2": "vsme:CapitalGoodsMember",
        "category3": "vsme:FuelAndEnergyRelatedActivitiesMember",
        "category4": "vsme:UpstreamTransportationAndDistributionMember",
        "category5": "vsme:WasteGeneratedInOperationsMember",
        "category6": "vsme:BusinessTravelMember",
        "category7": "vsme:EmployeeCommutingMember",
        "category8": "vsme:UpstreamLeasedAssetsMember",
        "category9": "vsme:DownstreamTransportationAndDistributionMember",
        "category10": "vsme:ProcessingOfSoldProductsMember",
        "category11": "vsme:UseOfSoldProductsMember",
        "category12": "vsme:EndOfLifeTreatmentOfSoldProductsMember",
        "category13": "vsme:DownstreamLeasedAssetsMember",
        "category14": "vsme:FranchisesMember",
        "category15": "vsme:InvestmentsMember",
    }
    
    # All 94 EFRAG Pollutants (from Regulation EU 2024/1244)
    POLLUTANTS = {
        "1,1,1-trichloroethane": "vsme:Trichloroethane-Member",
        "1,1,2,2-tetrachloroethane": "vsme:Tetrachloroethane-Member",
        "1,2,3,4,5,6-hexachlorocyclohexane (HCH)": "vsme:Hexachlorocyclohexane-Member",
        "1,2-dichloroethane (EDC)": "vsme:Dichloroethane-Member",
        "Alachlor": "vsme:Alachlor-Member",
        "Aldrin": "vsme:Aldrin-Member",
        "Ammonia (NH3)": "vsme:Ammonia-Member",
        "Anthracene": "vsme:Anthracene-Member",
        "Arsenic and compounds (As)": "vsme:Arsenic-Member",
        "Asbestos": "vsme:Asbestos-Member",
        "Atrazine": "vsme:Atrazine-Member",
        "Benzene": "vsme:Benzene-Member",
        "Chlorides (total Cl)": "vsme:Chlorides-Member",
        "Carbon dioxide (CO2)": "vsme:CarbonDioxide-Member",
        "Methane (CH4)": "vsme:Methane-Member",
        "Nitrogen oxides (NOx/NO2)": "vsme:NitrogenOxides-Member",
        "Nitrous oxide (N2O)": "vsme:NitrousOxide-Member",
        "Particulate matter (PM)": "vsme:ParticulateMatter-Member",
        "Sulphur oxides (SOx/SO2)": "vsme:SulphurOxides-Member",
    }
    
    WASTE_FALLBACK_MEMBER = "waste:W-WasteCategoriesMember"
    
    TREATMENT_METHODS = {
        "Recycling": "vsme:Recycling-Member",
        "Landfill": "vsme:Landfill-Member",
        "Incineration": "vsme:Incineration-Member",
        "Energy recovery": "vsme:EnergyRecovery-Member",
        "Other": "vsme:OtherTreatment-Member",
    }
    
    UNITS = {
        "kg": "utr:kg",
        "t": "utr:t",
        "tonn": "utr:t",
        "MWh": "utr:MWh",
        "m3": "utr:m3",
        "m³": "utr:m3",
        "EUR": "iso4217:EUR",
        "NOK": "iso4217:NOK",
        "tCO2e": "utr:tCO2e",
        "percent": "xbrli:pure",
        "count": "xbrli:pure",
        "km": "utr:sqkm"
    }
    
    def _unit(self, code: str, default: str = "xbrli:pure") -> str:
        return self.UNITS.get(code, default)

class XBRLFactBuilder:
	"""Collect facts in the payload format expected by the converter."""

	def __init__(self, entity_id: str, period_start: str, period_end: str):
		self.entity_id = entity_id
		self.period = f"{period_start}T00:00:00/{period_end}T00:00:00"
		self.facts: List[Dict[str, Any]] = []
		self.errors: List[str] = []

	def add_fact(
		self,
		concept: str,
		value: Any,
		unit: Optional[str] = None,
		decimals: Optional[int] = 2,
		dimensions: Optional[Any] = None,
	) -> bool:
		"""Append a fact unless its value is empty."""
		if value is None or value == "":
			return False

		fact: Dict[str, Any] = {
			"concept": concept,
			"entity": self.entity_id,
			"period": self.period,
			"value": value,
		}
		if unit:
			fact["unit"] = unit
		if decimals is not None:
			fact["decimals"] = decimals
		if dimensions:
			fact["dimensions"] = dimensions

		self.facts.append(fact)
		return True

	def get_facts(self) -> List[Dict[str, Any]]:
		return self.facts

	def get_errors(self) -> List[str]:
		return self.errors


class SectionMapper:
	"""Base class providing common access to input data and fact builder."""

	def __init__(self, data: Dict[str, Any], builder: XBRLFactBuilder):
		self.data = data
		self.builder = builder
