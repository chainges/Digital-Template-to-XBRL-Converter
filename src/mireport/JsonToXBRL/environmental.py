"""Mapper functions for environmental disclosures."""

from typing import Any, Dict, Optional

from .common import SectionMapper, XBRLFactBuilder, EFRAGTaxonomy


class EnvironmentalMapper(SectionMapper):
    """Maps energy, emissions, pollution, water, and resource use data."""

    def __init__(self, data: Dict[str, Any], builder: XBRLFactBuilder):
        super().__init__(data, builder)
        self.form_environmental = data.get("formEnvironmental", {})
        self.confidential_areas = data.get("confidentialAreas") or {}
        self.targets = data.get("targets") or {}
    
    def _read_numeric(self, value: Any) -> Optional[float]:
            if value is None or isinstance(value, bool):
                return None
            try:
                return float(str(value).strip())
            except (ValueError, AttributeError):
                return None
    
    
    def map_energy_sources(self) -> None:
        energyEmissions = self.form_environmental.get("energyEmissions") or {}
        
        nonRenewableElectricity = energyEmissions.get("nonRenewableElectricity") / 1000  # Assuming the original unit is kWh
        renewableElectricity = energyEmissions.get("renewableElectricity") / 1000  # Assuming the original unit is kWh
        selfGeneratedEnergy = energyEmissions.get("selfGeneratedEnergy") / 1000  # Assuming the original unit is kWh
        renewableFuels = energyEmissions.get("renewableFuels") / 1000  # Assuming the original unit is kWh
        
        totalRenewableAndNonRenewableElectricity = renewableElectricity + nonRenewableElectricity
        totalEnergyFromFuels = renewableFuels
        totalSelfGeneratedEnergy = selfGeneratedEnergy        
        
        self.builder.add_fact(
            concept="vsme:EnergyConsumptionFromElectricity",
            value=totalRenewableAndNonRenewableElectricity,
            unit=EFRAGTaxonomy()._unit("MWh"),
            decimals=2,
        )

        self.builder.add_fact(
            concept="vsme:EnergyConsumptionFromElectricity",
            value=renewableElectricity,
            unit=EFRAGTaxonomy()._unit("MWh"),
            decimals=2,
            dimensions={
                "dimension": "vsme:BreakdownOfEnergyConsumptionAxis",
                "member": "vsme:RenewableEnergyMember"
            }
        )

        self.builder.add_fact(
            concept="vsme:EnergyConsumptionFromElectricity",
            value=nonRenewableElectricity,
            unit=EFRAGTaxonomy()._unit("MWh"),
            decimals=2,
            dimensions={
                "dimension": "vsme:BreakdownOfEnergyConsumptionAxis",
                "member": "vsme:NonRenewableEnergyMember"
            }
        )

        self.builder.add_fact(
            concept="vsme:EnergyConsumptionFromSelfGeneratedElectricity",
            value=totalSelfGeneratedEnergy,
            unit=EFRAGTaxonomy()._unit("MWh"),
            decimals=2,
        )

        self.builder.add_fact(
            concept="vsme:EnergyConsumptionFromSelfGeneratedElectricity",
            value=selfGeneratedEnergy,
            unit=EFRAGTaxonomy()._unit("MWh"),
            decimals=2,
            dimensions={
                "dimension": "vsme:BreakdownOfEnergyConsumptionAxis",
                "member": "vsme:RenewableEnergyMember"
            }
        )

        self.builder.add_fact(
            concept="vsme:EnergyConsumptionFromSelfGeneratedElectricity",
            value=0,
            unit=EFRAGTaxonomy()._unit("MWh"),
            decimals=2,
            dimensions={
                "dimension": "vsme:BreakdownOfEnergyConsumptionAxis",
                "member": "vsme:NonRenewableEnergyMember"
            }
        )

        self.builder.add_fact(
            concept="vsme:EnergyConsumptionFromFuels",
            value=totalEnergyFromFuels,
            unit=EFRAGTaxonomy()._unit("MWh"),
            decimals=2,
        )

        self.builder.add_fact(
            concept="vsme:EnergyConsumptionFromFuels",
            value=renewableFuels,
            unit=EFRAGTaxonomy()._unit("MWh"),
            decimals=2,
            dimensions={
                "dimension": "vsme:BreakdownOfEnergyConsumptionAxis",
                "member": "vsme:RenewableEnergyMember"
            }
        )

        self.builder.add_fact(
            concept="vsme:EnergyConsumptionFromFuels",
            value=0,
            unit=EFRAGTaxonomy()._unit("MWh"),
            decimals=2,
            dimensions={
                "dimension": "vsme:BreakdownOfEnergyConsumptionAxis",
                "member": "vsme:NonRenewableEnergyMember"
            }
        )
        
        return
    
    def map_emissions(self) -> None:
        energyEmissions = self.form_environmental.get("energyEmissions")
        
        scope1Emissions = energyEmissions.get("scope1Emissions", 0.0)
        scope2EmissionsLocationBased = energyEmissions.get("scope2EmissionsLocationBased", 0.0)
        scope2EmissionsMarketBased = energyEmissions.get("scope2EmissionsMarketBased", 0.0)
        scope3Emissions = energyEmissions.get("totalScope3Emissions", 0.0)
        
        self.builder.add_fact(
            "vsme:GrossScope1GreenhouseGasEmissions",
            scope1Emissions,
            decimals=2,
            unit=EFRAGTaxonomy()._unit("tCO2e"),
        )
        
        self.builder.add_fact(
            "vsme:GrossLocationBasedScope2GreenhouseGasEmissions",
            scope2EmissionsLocationBased,
            decimals=2,
            unit=EFRAGTaxonomy()._unit("tCO2e"),
        )
        
        
        self.builder.add_fact(
            "vsme:TotalGrossLocationBasedScope1AndScope2GHGEmissions",
            scope1Emissions + scope2EmissionsLocationBased,
            decimals=2,
            unit=EFRAGTaxonomy()._unit("tCO2e"),
        )
        
        self.builder.add_fact(
            "vsme:GrossMarketBasedScope2GreenhouseGasEmissions",
            scope2EmissionsMarketBased,
            decimals=2,
            unit=EFRAGTaxonomy()._unit("tCO2e"),
        )
        
        self.builder.add_fact(
            "vsme:TotalGrossMarketBasedScope1AndScope2GHGEmissions",
            scope1Emissions + scope2EmissionsMarketBased,
            decimals=2,
            unit=EFRAGTaxonomy()._unit("tCO2e"),
        )
        
        self.builder.add_fact(
            "vsme:GrossScope3GreenhouseGasEmissions",
            scope3Emissions,
            decimals=2,
            unit=EFRAGTaxonomy()._unit("tCO2e"),
        )

        # self.builder.add_fact(
        #     concept= "vsme:TotalLocationBasedGreenhouseGasEmissionsIntensityValue",
        #     value=(scope2EmissionsLocationBased) / turnover if turnover else None,
        #     decimals=2,
        #     unit=EFRAGTaxonomy()._unit("tCO2e"),
        # )
        
        # self.builder.add_fact(
        #     concept= "vsme:TotalMarketBasedGreenhouseGasEmissionsIntensityValue",
        #     value=(scope2EmissionsMarketBased) / turnover if turnover else None,
        #     decimals=2,
        #     unit=EFRAGTaxonomy()._unit("tCO2e"),
        # )

    def map_energy_emissions(self) -> None:
        
        if "vsme:B3-EnergyAndGreenhouseGasEmissionsMember" in self.confidential_areas:
            return
        
        energyEmissions = self.form_environmental.get("energyEmissions")
        # confidentialAreas = self.confidential_areas
        
        totalEnergyConsumption = energyEmissions.get("totalEnergyConsumption")
        
        ### covert total energy consumption into MWh
        if totalEnergyConsumption is not None:
            totalEnergyConsumptionMWh = totalEnergyConsumption / 1000  # Assuming the original unit is kWh
            self.builder.add_fact(
                "vsme:TotalEnergyConsumption",
                round(totalEnergyConsumptionMWh, 2),
                unit=EFRAGTaxonomy()._unit("MWh"),
                decimals=2
            )
        
        if "vsme:B3BreakdownOfEnergyConsumptionInMWhMember" not in self.confidential_areas:
        
            self.map_energy_sources()
        
        if "vsme:B3EstimatedGreenhouseGasEmissionsConsideringTheGHGProtocolVersion2004InTCO2eMember" not in self.confidential_areas:
            self.map_emissions()
        
        ### TODO: implement turnover-based emissions intensity mapping
        
        
        return

    def map_pollution(self) -> None:
        pollution = self.form_environmental.get("pollution")
        
        confidentialAreas = self.confidential_areas
        
        if "vsme:B4-PollutionOfAirWaterAndSoilMember" in confidentialAreas:
            return

        publiclyAvailableDisclosure = pollution.get("publiclyAvailableDisclosure")
        
        self.builder.add_fact(
            "vsme:PubliclyAvailableDisclosure",
            publiclyAvailableDisclosure,
            unit=EFRAGTaxonomy()._unit("boolean"),
            decimals=0
        )

        pollutants = pollution.get("pollutants") or []
        
        for item in pollutants:
            raw_code = item.get("pollutantCode", "").strip()

            # EFRAG taxonomy uses format: "vsme:<PollutantName>Member"
            pollutant_member = f"vsme:{raw_code}Member"

            unit_code = item.get("unitCode")

            air = item.get("amountOfEmissionToAir")
            water = item.get("amountOfEmissionToWater")
            soil = item.get("amountOfEmissionToSoil")

            if unit_code == "t":
                air = round(air * 1000.0, 2) if air is not None else None
                water = round(water * 1000.0, 2) if water is not None else None
                soil = round(soil * 1000.0, 2) if soil is not None else None

            unit_code = "kg" if unit_code == "kg" else unit_code
            unit_tag = f"utr:{unit_code}" if unit_code else "utr:kg"
            media_facts = [
                ("vsme:AmountOfEmissionToAir", air),
                ("vsme:AmountOfEmissionToWater", water),
                ("vsme:AmountOfEmissionToSoil", soil),
            ]

            for concept_name, val in media_facts:
                if val is not None and val > 0:
                    dimensions = {
                        "dimension": "vsme:TypeOfPollutantAxis",
                        "member": pollutant_member,
                    }

                    self.builder.add_fact(
                        concept=concept_name,
                        value=round(val, 2),
                        unit=unit_tag,
                        decimals=2,
                        dimensions=dimensions,
                    )

        return

    def map_biodiversity(self) -> None:
        biodiversity = self.form_environmental.get("biodiversity")
        
        confidentialAreas = self.confidential_areas
        
        hasSensitiveBiodiversityAreas = biodiversity.get("hasSensitiveBiodiversityAreas")
        
        if "vsme:B5SitesInBiodiversitySensitiveAreasMember" not in confidentialAreas and hasSensitiveBiodiversityAreas:
            sites = biodiversity.get("sites")
            for site in sites:
                self.builder.add_fact(
                    concept="vsme:AreaOfSiteInBiodiversitySensitiveArea",
                    value=site.get("areaOfSiteInBiodiversitySensitiveArea"),
                    #unit=EFRAGTaxonomy()._unit("ha"),
                    decimals=2,
                    dimensions= {
                        "dimension":"vsme:IdentifierOfSiteTypedAxis",
                        "typedValue": 1
                    }
                )
            
                self.builder.add_fact(
                    concept = "vsme:SiteLocatedInABiodiversitySensitiveArea",
                    value = hasSensitiveBiodiversityAreas,
                    decimals = 0,
                    unit=EFRAGTaxonomy()._unit("boolean"),
                    dimensions={
                        "dimension":"vsme:IdentifierOfSiteTypedAxis",
                        "typedValue": 1
                    }
                )
            
                self.builder.add_fact(
                    concept = "vsme:SiteLocatedNearABiodiversitySensitiveArea",
                    value = not hasSensitiveBiodiversityAreas ,
                    decimals = 0,
                    unit=EFRAGTaxonomy()._unit("boolean"),
                    dimensions={
                        "dimension":"vsme:IdentifierOfSiteTypedAxis",
                        "typedValue": 1
                    }
                )
        
        if "vsme:B5BiodiversityLandUseMember" in confidentialAreas:
            return
        
        ## convert square meters to square kilometers
        
        totalLandUsedSquareMeters = biodiversity.get("totalLandUsedSquareMeters") / 10000 if biodiversity.get("totalLandUsedSquareMeters") is not None else None
        totalNatureOrientedAreaOffSiteSquareMeters = biodiversity.get("totalNatureOrientedAreaOffSiteSquareMeters") / 10000 if biodiversity.get("totalNatureOrientedAreaOffSiteSquareMeters") is not None else None
        totalNatureOrientedAreaOnSiteSquareMeters = biodiversity.get("totalNatureOrientedAreaOnSiteSquareMeters") / 10000 if biodiversity.get("totalNatureOrientedAreaOnSiteSquareMeters") is not None else None
        totalSealedAreaSquareMeters = biodiversity.get("totalSealedAreaSquareMeters") / 10000 if biodiversity.get("totalSealedAreaSquareMeters") is not None else None
        
        if totalLandUsedSquareMeters is not None:
            self.builder.add_fact(
                "vsme:TotalUseOfLand",
                totalLandUsedSquareMeters,
                #unit=EFRAGTaxonomy()._unit("km"),
                decimals=2
            )
        
        if totalNatureOrientedAreaOffSiteSquareMeters is not None:
            self.builder.add_fact(
                "vsme:TotalNatureOrientedAreaOffSite",
                totalNatureOrientedAreaOffSiteSquareMeters,
                #unit=EFRAGTaxonomy()._unit("km"),
                decimals=2
            )
        
        if totalNatureOrientedAreaOnSiteSquareMeters is not None:
            self.builder.add_fact(
                "vsme:TotalNatureOrientedAreaOnSite",
                totalNatureOrientedAreaOnSiteSquareMeters,
                #unit=EFRAGTaxonomy()._unit("km"),
                decimals=2
            )
        
        if totalSealedAreaSquareMeters is not None:
            self.builder.add_fact(
                "vsme:TotalSealedArea",
                totalSealedAreaSquareMeters,
                #unit=EFRAGTaxonomy()._unit("km"),
                decimals=2
            )
        
        return
    
    def map_annual_mass_flows(self) -> None:
        
        resourceUseCircularEconomy = self.form_environmental.get("resourceUseCircularEconomy", {})
        
        annualMassFlows = resourceUseCircularEconomy.get("annualMassFlows")
        total_mass_kg = 0.0
        total_volume_m3 = 0.0
        
        for idx, flow in enumerate(annualMassFlows or [], start=1):
            material_type = flow.get("materialType", "Unknown Material")
            raw_unit = str(flow.get("unit", "")).strip().lower()
            weight = flow.get("volume")
            
            volume_val = None

            if weight is None:
                continue

            axis_key = str(idx)
            
            if(raw_unit == "tonn"):
                weight = weight * 1000.0  # Convert tonnes to kg for internal calculations
            
            if(raw_unit == "mâ³"):
                volume_val = weight  # Volume in m³
                weight = None  # Weight not provided in this case

            dimensions = {
                "dimension": "vsme:IdentifierOfMaterialTypedAxis",
                "typedValue": int(axis_key),
            }

            # 1. Fact: Name of the material used
            self.builder.add_fact(
                concept="vsme:NameOfMaterialUsed",
                value=material_type,
                dimensions=dimensions,
            )
            
            if volume_val is None:
                self.builder.add_fact(
                    concept="vsme:WeightOfMaterialUsed",
                    value=weight,
                    unit=EFRAGTaxonomy()._unit("kg"),
                    decimals=2,
                    dimensions=dimensions,
                )
            else:
                self.builder.add_fact(
                    concept="vsme:VolumeOfMaterialUsed",
                    value=volume_val,
                    unit=EFRAGTaxonomy()._unit("m3"),
                    decimals=2,
                    dimensions=dimensions,
                )
                
            if weight is not None:
                total_mass_kg += weight
            
            if volume_val is not None:
                total_volume_m3 += volume_val
                
        self.builder.add_fact(
            concept="vsme:TotalMassOfMaterialUsed",
            value=round(total_mass_kg, 2),
            unit=EFRAGTaxonomy()._unit("kg"),
            decimals=2
        )

        
        self.builder.add_fact(
            concept="vsme:TotalVolumeOfMaterialUsed",
            value=round(total_volume_m3, 2),
            unit=EFRAGTaxonomy()._unit("m3"),
            decimals=2
        )
        
        return

    def map_waste(self) -> None:
        resourceUseCircularEconomy = self.form_environmental.get("resourceUseCircularEconomy") 
        wasteInformation = resourceUseCircularEconomy.get("wasteInformation")
        
        totalHazadiousWasteMass = 0
        totalNonHazadiousWasteMass = 0
        totalWasteMass = 0
        
        totalHazadiousWasteVolume = 0
        totalNonHazadiousWasteVolume = 0
        totalWasteVolume = 0
        
        
        for waste in wasteInformation:
            
            total = waste.get("total")
            unit = waste.get("unit")
            hazardous = waste.get("hazardous")
            wasteDirectedToDisposal = waste.get("wasteDirectedToDisposal")
            wasteDivertedToRecycle = waste.get("wasteDivertedToRecycle")
            
            axis = waste.get("axis")
            
            
            if hazardous:
                if unit == "mÂ³":
                    totalHazadiousWasteVolume += total
                else:
                    if unit == "kg":
                        totalHazadiousWasteMass += total
                    totalHazadiousWasteMass += total*1000
            else:
                if unit == "mÂ³":
                    totalNonHazadiousWasteVolume += total
                else:
                    if unit == "kg":
                        totalNonHazadiousWasteMass += total
                    totalNonHazadiousWasteMass += total*1000
            
            if unit == "mÂ³":
                totalWasteVolume += total
            else:
                totalWasteMass += total
            
            Type = "Volume" if unit == "mÂ³" else "Mass" 
            
            self.builder.add_fact(
                concept=f"vsme:WasteDivertedToRecycleOrReuse{Type}",
                value=wasteDivertedToRecycle,
                unit=EFRAGTaxonomy()._unit(unit),
                decimals=2,
                dimensions={
                    "dimension":"vsme:TypeOfWasteAxis",
                    "member":axis
                }
            )
            
            self.builder.add_fact(
                concept=f"vsme:WasteDirectedToDisposal{Type}",
                value=wasteDirectedToDisposal,
                unit=EFRAGTaxonomy()._unit(unit),
                decimals=2,
                dimensions={
                    "dimension":"vsme:TypeOfWasteAxis",
                    "member":axis
                }
            )
            
            self.builder.add_fact(
                concept=f"vsme:TotalWasteRecycledReusedAndDirectedToDisposal{Type}",
                value=total,
                unit=EFRAGTaxonomy()._unit(unit),
                decimals=2,
                dimensions={
                    "dimension":"vsme:TypeOfWasteAxis",
                    "member":axis
                }
            )
            
        self.builder.add_fact(
            "vsme:TotalHazardousWasteGeneratedMass",
            totalHazadiousWasteMass,
            unit=EFRAGTaxonomy()._unit("kg"),
            decimals=2
        )
        
        self.builder.add_fact(
            "vsme:TotalNonHazardousWasteGeneratedMass",
            totalNonHazadiousWasteMass,
            unit=EFRAGTaxonomy()._unit("kg"),
            decimals=2
        )
        
        self.builder.add_fact(
            "vsme:TotalWasteGeneratedMass",
            totalWasteMass,
            unit=EFRAGTaxonomy()._unit("kg"),
            decimals=2
        )
        
        self.builder.add_fact(
            "vsme:TotalHazardousWasteGeneratedVolume",
            totalHazadiousWasteVolume,
            unit=EFRAGTaxonomy()._unit("m³"),
            decimals=2
        )
        
        self.builder.add_fact(
            "vsme:TotalNonHazardousWasteGeneratedVolume",
            totalNonHazadiousWasteVolume,
            unit=EFRAGTaxonomy()._unit("m³"),
            decimals=2
        )
        
        self.builder.add_fact(
            "vsme:TotalWasteGeneratedVolume",
            totalWasteVolume,
            unit=EFRAGTaxonomy()._unit("m³"),
            decimals=2
        )
        
            
        return
    
    def map_circular_economy(self) -> None:
        resourceUseCircularEconomy = self.form_environmental.get("resourceUseCircularEconomy")
        confidentialAreas = self.confidential_areas
        
        if "vsme:B7-ResourceUseCircularEconomyAndWasteManagementMember" in confidentialAreas:
            return
        
        applyCircularEconomyPrinciples = resourceUseCircularEconomy.get("applyCircularEconomyPrinciples")
        
        self.builder.add_fact(
            "vsme:UndertakingAppliesCircularEconomyPrinciples",
            applyCircularEconomyPrinciples,
            unit=EFRAGTaxonomy()._unit("boolean"),
            decimals=0
        )
        
        if not "vsme:B7DescriptionOfCircularEconomyPrinciplesMember" in confidentialAreas:
        
            circularEconomyDescription = resourceUseCircularEconomy.get("circularEconomyDescription")
            self.builder.add_fact(
                "vsme:DescriptionOfHowCircularEconomyPrinciplesAreApplied",
                circularEconomyDescription,
                unit=EFRAGTaxonomy()._unit("string"),
                decimals=0
            )
        
        if "vsme:B7AnnualMassFlowOfRelevantMaterialsUsedMember" not in confidentialAreas:
            self.map_annual_mass_flows()
        
        
        if "vsme:B7WasteGeneratedMember" not in confidentialAreas:
            self.map_waste()
        
        return

    def map_annual_waste(self) -> None:
        """TODO: Map materials used and waste generated."""
        pass

    def map_emission_targets(self) -> None:
        

        baseYear = self.targets.get("baseYear")
        targetYear = self.targets.get("targetYear")
        
        climateTransitionPlanDescription = self.targets.get("climateTransitionPlanDescription", None)
        
        keyActionsToReachTargets = self.targets.get("keyActionsToReachTargets", None)
        
        self.builder.add_fact(
            "vsme:GreenhouseGasEmissionReductionTargetBaseYear",
            baseYear,
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )
        
        self.builder.add_fact(
            "vsme:GreenhouseGasEmissionReductionTargetYear",
            targetYear,
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )
        
        targetReduction = self.targets.get("targetReduction") or 0.0
        
        if(targetReduction > 1.0):
            targetReduction = targetReduction / 100.0
        
        #print("Target Reduction: ", targetReduction)
        
        baseLineEmissions = self.targets.get("projections")[0]
        
        scope1,scope2, scope3 = baseLineEmissions.get("scope1"), baseLineEmissions.get("scope2"), baseLineEmissions.get("scope3")
        
        t_scope1,t_scope2, t_scope3 = self._read_numeric(scope1)*targetReduction, self._read_numeric(scope2)*targetReduction, self._read_numeric(scope3)*targetReduction
        
        targetScope1, targetScope2, targetScope3 = scope1-t_scope1, scope2-t_scope2, scope3-t_scope3
        
        self.builder.add_fact(
            concept="vsme:GrossScope1GreenhouseGasEmissions",
            unit=EFRAGTaxonomy()._unit("tCO2e"),
            value=round(scope1,2),
            decimals=2,
            dimensions = {
                "dimension": "vsme:ReportingScopesAxis",
                "member": "vsme:BaselineYearMember"
            }
        )
        
        self.builder.add_fact(
            concept="vsme:GrossScope1GreenhouseGasEmissions",
            unit=EFRAGTaxonomy()._unit("tCO2e"),
            value=round(targetScope1,2),
            decimals=2,
            dimensions = {
                "dimension": "vsme:ReportingScopesAxis",
                "member": "vsme:TargetYearMember"
            }
        )

        self.builder.add_fact(
            concept="vsme:GrossLocationBasedScope2GreenhouseGasEmissions",
            unit=EFRAGTaxonomy()._unit("tCO2e"),
            value=round(scope2,2),
            decimals=2,
            dimensions = {
                "dimension": "vsme:ReportingScopesAxis",
                "member": "vsme:BaselineYearMember"
            }
        )
        
        self.builder.add_fact(
            concept="vsme:GrossLocationBasedScope2GreenhouseGasEmissions",
            unit=EFRAGTaxonomy()._unit("tCO2e"),
            value=round(targetScope2,2),
            decimals=2,
            dimensions = {
                "dimension": "vsme:ReportingScopesAxis",
                "member": "vsme:TargetYearMember"
            }
        )
        self.builder.add_fact(
            concept="vsme:TotalGrossLocationBasedScope1AndScope2GHGEmissions",
            unit=EFRAGTaxonomy()._unit("tCO2e"),
            value=round(scope1+scope2,2),
            decimals=2,
            dimensions = {
                "dimension": "vsme:ReportingScopesAxis",
                "member": "vsme:BaselineYearMember"
            }
        )
        
        self.builder.add_fact(
            concept="vsme:TotalGrossLocationBasedScope1AndScope2GHGEmissions",
            unit=EFRAGTaxonomy()._unit("tCO2e"),
            value=round(targetScope1+targetScope2,2),
            decimals=2,
            dimensions = {
                "dimension": "vsme:ReportingScopesAxis",
                "member": "vsme:TargetYearMember"
            }
        )

        self.builder.add_fact(
            concept="vsme:GrossScope3GreenhouseGasEmissions",
            unit=EFRAGTaxonomy()._unit("tCO2e"),
            value=round(scope3,2),
            decimals=2,
            dimensions = {
                "dimension": "vsme:ReportingScopesAxis",
                "member": "vsme:BaselineYearMember"
            }
        )
        
        self.builder.add_fact(
            concept="vsme:GrossScope3GreenhouseGasEmissions",
            unit=EFRAGTaxonomy()._unit("tCO2e"),
            value=round(targetScope3,2),
            decimals=2,
            dimensions = {
                "dimension": "vsme:ReportingScopesAxis",
                "member": "vsme:TargetYearMember"
            }
        )
        
        self.builder.add_fact(
            concept= "vsme:TotalGrossLocationBasedGHGEmissions",
            unit=EFRAGTaxonomy()._unit("tCO2e"),
            value=round(scope1+scope2+scope3,2),
            decimals=2,
            dimensions = {
                "dimension": "vsme:ReportingScopesAxis",
                "member": "vsme:BaselineYearMember"
            }
        )
        
        self.builder.add_fact(
            concept= "vsme:TotalGrossLocationBasedGHGEmissions",
            unit=EFRAGTaxonomy()._unit("tCO2e"),
            value=round(targetScope1+targetScope2+targetScope3,2),
            decimals=2,
            dimensions = {
                "dimension": "vsme:ReportingScopesAxis",
                "member": "vsme:TargetYearMember"
            }
        )
        
        if climateTransitionPlanDescription is not None:
        
            self.builder.add_fact(
                "vsme:DisclosureOfListOfMainActionsTheEntitySeeksInOrderToAchieveItsTargets",
                climateTransitionPlanDescription,
                unit=EFRAGTaxonomy()._unit("text"),
                decimals=0
            )
        
        if keyActionsToReachTargets is not None:
            self.builder.add_fact(
                "vsme:DescriptionOfATransitionPlanForClimateChangeMitigationIncludingAnExplanationOfHowItIsContributingToReduceGhgEmissions",
                keyActionsToReachTargets,
                unit=EFRAGTaxonomy()._unit("text"),
                decimals=0
            )

    def map_climate_risk(self) -> None:
        cr = self.form_environmental.get("climateRiskAnalysis", None)
        
        if "vsme:C4-ClimateRisksMember" in self.confidential_areas or cr is None:
            return
                
        climateRiskDescription = cr.get("climateRiskDescription", "")
        
        exposureAndSensitivityAssessment = cr.get("exposureAndSensitivityAssessment", "")
        
        potentialAdverseEffectsAndRiskRating = cr.get("potentialAdverseEffectsAndRiskRating", None)
        
        timeHorizonsIdentified = cr.get("timeHorizonsIdentified", "")
        
        hasIdentifiedClimateRelatedHazardious = cr.get("hasIdentifiedClimateRelatedHazardious", "")
                
        self.builder.add_fact(
            "vsme:DescriptionOfClimateRelatedHazardsAndClimateRelatedTransitionEvents",
            climateRiskDescription,
            unit=EFRAGTaxonomy()._unit("text"),
            decimals=0
        )
        
        self.builder.add_fact(
            "vsme:DisclosureOfHowItHasAssessedTheExposureAndSensitivityOfItsAssetsActivitiesAndValueChainToTheseHazardsAndTransitionEvents",
            exposureAndSensitivityAssessment,
            unit=EFRAGTaxonomy()._unit("text"),
            decimals=0
        )
        
        self.builder.add_fact(
            "vsme:TimeHorizonsOfAnyClimateRelatedHazardsAndTransitionEventsIdentified",
            timeHorizonsIdentified,
            unit=EFRAGTaxonomy()._unit("text"),
            decimals=0
        )
        
        
        self.builder.add_fact(
            "vsme:DisclosureOfWhetherItHasUndertakenClimateChangeAdaptationActionsForAnyClimateRelatedHazardsAndTransitionEvents",
            hasIdentifiedClimateRelatedHazardious,
            unit=EFRAGTaxonomy()._unit("text"),
            decimals=0
        )
        
        if potentialAdverseEffectsAndRiskRating is not None:
            self.builder.add_fact(
                "vsme:PotentialAdverseEffectsOfClimateRisksThatMayAffectItsFinancialPerformanceOrBusinessOperationsInTheShortMediumOrLongTermIndicatingWhetherItAssessesTheRisksToBeHighMediumOrLow",
                potentialAdverseEffectsAndRiskRating,
                unit=EFRAGTaxonomy()._unit("text"),
                decimals=0
            )

    def map_water(self) -> None:
        water = self.form_environmental.get("waterManagement", {})
        
        if "vsme:B6-WaterMember" in self.confidential_areas:
            return
        
        waterConsumption = water.get("waterConsumption", "")
        waterDischarge = water.get("waterDischarge", "")
        waterWithdrawal = water.get("waterWithdrawal", "")
        waterWithdrawalStress = water.get("waterWithdrawalStress", "")
        

        self.builder.add_fact(
            "vsme:TotalWaterConsumption",
            waterConsumption,
            unit=EFRAGTaxonomy()._unit("text"),
            decimals=0
        )

        self.builder.add_fact(
            "vsme:WaterDischargeFromUndertakingProductionProcesses",
            waterDischarge,
            unit=EFRAGTaxonomy()._unit("text"),
            decimals=0
        )

        self.builder.add_fact(
            "vsme:TotalAmountOfWaterWithdrawnFromAllSites",
            waterWithdrawal,
            unit=EFRAGTaxonomy()._unit("text"),
            decimals=0
        )

        self.builder.add_fact(
            "vsme:AmountOfWaterWithdrawnAtSitesLocatedInAreasOfHighWaterStress",
            waterWithdrawalStress,
            unit=EFRAGTaxonomy()._unit("text"),
            decimals=0
        )

    def map_all(self) -> None:
        self.map_energy_emissions()
        self.map_pollution()
        self.map_biodiversity()
        self.map_circular_economy()
        self.map_annual_waste()
        self.map_emission_targets()
        self.map_climate_risk()
        self.map_water()