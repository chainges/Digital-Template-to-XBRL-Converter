"""Mapper functions for governance disclosures."""

from typing import Any, Dict

from .common import SectionMapper, XBRLFactBuilder


class GovernanceMapper(SectionMapper):
    """Maps business conduct and governance-body data."""

    def __init__(self, data: Dict[str, Any], builder: XBRLFactBuilder):
        super().__init__(data, builder)
        self.form_governance = data.get("formGovernance", {})
        self.builder = builder
        self.confidentialAreas = self.form_governance.get("confidentialAreas", [])
    
    def map_finesPenalties(self) -> None:
        finesPenalties = self.form_governance.get("finesPenalties", [])
        numberOfConvictions = finesPenalties.get("numberOfConvictions", 0)
        totalFines = finesPenalties.get("totalFines", 0)
        
        hasCorruptionFines = finesPenalties.get("hasCorruptionFines", False)
        
        
        if not hasCorruptionFines:
            return
        
        self.builder.add_fact(
            "vsme:TotalNumberOfConvictionsForTheViolationOfAntiCorruptionAndAntiBriberyLaws",
            numberOfConvictions,
            decimals=0
        )
        
        self.builder.add_fact(
            "vsme:TotalAmountOfFinesForTheViolationOfAnticorruptionAndAntibriberyLaws",
            totalFines,
            decimals=0
        )

    def map_sectors_involved(self) -> None:
        sectorInvolvement = self.form_governance.get("sectorInvolvement", [])
        
        controversialWeaponsRevenue = sectorInvolvement.get("controversialWeaponsRevenue", None)
        
        tobaccoRevenue = sectorInvolvement.get("tobaccoRevenue", None)
        
        coalRevenue = sectorInvolvement.get("coalRevenue", None)
        
        gasRevenue = sectorInvolvement.get("gasRevenue", None)
        
        oilRevenue = sectorInvolvement.get("oilRevenue", None)
        
        chemicalProductionRevenue = sectorInvolvement.get("chemicalProductionRevenue", None)
        
        euBenchmarksExclusion = sectorInvolvement.get("euBenchmarksExclusion", False)
        
        if controversialWeaponsRevenue is not None:
            self.builder.add_fact(
                "vsme:RevenueDerivedFromControversialWeaponsAntiPersonnelMinesClusterMunitionsChemicalWeaponsAndBiologicalWeapons",
                controversialWeaponsRevenue,
                decimals=0
            )
        
        if tobaccoRevenue is not None:
            self.builder.add_fact(
                "vsme:RevenueDerivedFromCultivationAndProductionOfTobacco",
                tobaccoRevenue,
                decimals=0
            )
        
        if coalRevenue is not None:
            self.builder.add_fact(
                "vsme:RevenueDerivedFromCoal",
                coalRevenue,
                decimals=0
            )
        
        if gasRevenue is not None:
            self.builder.add_fact(
                "vsme:RevenueDerivedFromGas",
                gasRevenue,
                decimals=0
            )
        
        if oilRevenue is not None:
            self.builder.add_fact(
                "vsme:RevenueDerivedFromOil",
                oilRevenue,
                decimals=0
            )
        
        if chemicalProductionRevenue is not None:
            self.builder.add_fact(
                "vsme:RevenueDerivedFromChemicalProduction",
                chemicalProductionRevenue,
                decimals=0
            )
        
        self.builder.add_fact(
            "vsme:UndertakingsAreExcludedFromAnyEuReferenceBenchmarksThatAreAlignedWithTheParisAgreement",
            euBenchmarksExclusion,
            decimals=0
        )
    
    def map_Gender_Diversity(self) -> None:
        boardComposition = self.form_governance.get("boardComposition", [])
        
        femaleMembers = boardComposition.get("femaleMembers", 0)
        maleMembers = boardComposition.get("maleMembers", 0)
        
        ratio =0
        
        if maleMembers == 0:
            ratio = femaleMembers
        else:
            ratio = femaleMembers / maleMembers
        
        
        self.builder.add_fact(
            "vsme:GenderDiversityRatioInGovernanceBody",
            ratio,
            decimals=2
        )

    def map_all(self) -> None:
        self.map_sectors_involved()
        self.map_finesPenalties()
        self.map_Gender_Diversity()