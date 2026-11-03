"""Mapper functions for workforce and human-rights disclosures."""

from typing import Any, Dict

from .common import EFRAGTaxonomy, SectionMapper, XBRLFactBuilder


class SocialMapper(SectionMapper):
    """Maps workforce, health and safety, and human-rights data."""

    def __init__(self, data: Dict[str, Any], builder: XBRLFactBuilder):
        super().__init__(data, builder)
        self.form_social = data.get("formSocial", {})
        self.confidential_areas = data.get("confidentialAreas", [])
        
    def mapNumberOfEmployeesForCountryOfEmploymentContract(self) -> None:
        workforce = self.form_social.get("workforce", {})
        employeesPerCountry = workforce.get("employeesPerCountry", [])
        
        for idx, country_data in enumerate(employeesPerCountry or [], start=1):
            country_code = country_data.get("country")
            numberOfEmployees = country_data.get("numberOfEmployees") or 0
            
            self.builder.add_fact(
                "vsme:NumberOfEmployeesForCountryOfEmploymentContract",
                numberOfEmployees,
                unit=EFRAGTaxonomy()._unit("count"),
                decimals=0,
                dimensions={
                    "dimension": "vsme:CountryOfEmploymentContractAxis",
                    "member": f"country:{country_code}" if not country_code.startswith("country:") else country_code,
                }
            )

    def map_workforce(self) -> None:
        workforce = self.form_social.get("workforce", {})

        if "vsme:B8-WorkforceGeneralCharacteristicsMember" in self.confidential_areas:
            return
        
        permanentContractEmployees = workforce.get("permanentContractEmployees", 0)
        
        temporaryContractEmployees = workforce.get("temporaryContractEmployees", 0)
        
        men = workforce.get("men", 0)
        women = workforce.get("women", 0)
        other = workforce.get("other", 0)
        nonReported = workforce.get("nonReported", 0)
        
        self.builder.add_fact(
            "vsme:NumberOfPermanentContractEmployees",
            permanentContractEmployees,
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )
        
        self.builder.add_fact(
            "vsme:NumberOfTemporaryContractEmployees",
            temporaryContractEmployees,
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )
        
        self.builder.add_fact(
            "vsme:NumberOfMaleEmployees",
            men,
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )
        self.builder.add_fact(
            "vsme:NumberOfFemaleEmployees",
            women,
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )
        self.builder.add_fact(
            "vsme:NumberOfOtherGenderEmployees",
            other,  # Fallback to 'other' gender employees
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )
        self.builder.add_fact(
            "vsme:NumberOfNonReportedGenderEmployees",
            nonReported,
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )

        if "vsme:B8CountryOfEmploymentMember" not in self.confidential_areas:
            self.mapNumberOfEmployeesForCountryOfEmploymentContract()
        
        if "vsme:B8TurnoverRateMember" not in self.confidential_areas:
            employeeTurnoverRate = workforce.get("employeeTurnoverRate", 0)
            
            self.builder.add_fact(
                "vsme:EmployeeTurnoverRate",
                round(employeeTurnoverRate, 2),
                unit=EFRAGTaxonomy()._unit("percent"),
                decimals=2
            )


    def map_health_safety(self) -> None:
        healthSafety = self.form_social.get("healthSafety", {})
        workAccidents = healthSafety.get("workAccidents", 0)
        rateOfWorkAccidents = healthSafety.get("rateOfWorkAccidents", 0)
        hmsTraining = healthSafety.get("hmsTraining", 0)
        sicknessAbsencePercentage = healthSafety.get("sicknessAbsencePercentage", 0)
        
        self.builder.add_fact(
            "vsme:NumberOfRecordableWorkRelatedAccidentsInTheReportingPeriod",
            workAccidents,
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )
        self.builder.add_fact(
            "vsme:RateOfRecordableWorkRelatedAccidentsInTheReportingPeriod",
            round(rateOfWorkAccidents, 2),
            unit=EFRAGTaxonomy()._unit("percent"),
            decimals=2
        )
    
    def mapCompensationCollectiveBargaining(self) -> None:
        compensationCollectiveBargaining = self.form_social.get("compensationCollective", {})
        minimumWageLiability = compensationCollectiveBargaining.get("minimumWageLiability", 0)
        
        genderPayGap = compensationCollectiveBargaining.get("genderPayGap", 0)
        
        collectiveBargainingShare = compensationCollectiveBargaining.get("collectiveBargainingShare", 0)
        
        trainingHoursFemale = compensationCollectiveBargaining.get("trainingHoursFemale", 0)
        
        trainingHoursMale = compensationCollectiveBargaining.get("trainingHoursMale", 0)
        

        self.builder.add_fact(
            "vsme:EmployeesReceivePayEqualOrAboveMinimumWageDeterminedByNationalLawOrCollectiveAgreement",
            minimumWageLiability,
            unit=EFRAGTaxonomy()._unit("boolean"),
        )
        
        self.builder.add_fact(
            "vsme:PercentageGapInPayBetweenFemaleAndMaleEmployees",
            round(genderPayGap*100, 2),
            unit=EFRAGTaxonomy()._unit("percent"),
            decimals=2
        )
        
        self.builder.add_fact(
            "vsme:PercentageOfEmployeesCoveredByCollectiveBargainingAgreements",
            round(collectiveBargainingShare*100, 2),
            unit=EFRAGTaxonomy()._unit("percent"),
            decimals=2
        )
        
        self.builder.add_fact(
            "vsme:AverageNumberOfAnnualTrainingHoursPerFemaleEmployee",
            trainingHoursFemale,
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )
        
        self.builder.add_fact(
            "vsme:AverageNumberOfAnnualTrainingHoursPerMaleEmployee",
            trainingHoursMale,
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )

    def map_additional_workforce_metrics(self) -> None:
        additionalWorkforce = self.form_social.get("additionalWorkforce", {})
        
        managementGenderRatio = additionalWorkforce.get("managementGenderRatio", 0)
        
        contractWorkers = additionalWorkforce.get("contractWorkers", 0)
        
        selfEmployedWorkers = additionalWorkforce.get("selfEmployedWorkers", 0)
        
        self.builder.add_fact(
            "vsme:FemaleToMaleRatioAtManagementLevelForTheReportingPeriod",
            managementGenderRatio,
            unit=EFRAGTaxonomy()._unit("ratio"),
            decimals=2
        )
        
        self.builder.add_fact(
            "vsme:TotalNumberOfSelfEmployedWorkersWithoutPersonnelThatAreWorkingExclusivelyForTheUndertaking",
            selfEmployedWorkers,
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )
        
        self.builder.add_fact(
            "vsme:TotalNumberOfTemporaryWorkersProvidedByUndertakingsPrimarilyEngagedInEmploymentActivities",
            contractWorkers,
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )

    def map_human_rights(self) -> None:
        humanRightsPolicies = self.form_social.get("humanRightsPolicies", {})
        
        hasCodeOfConduct = humanRightsPolicies.get("hasCodeOfConduct", False)
        
        childLaborPolicy = humanRightsPolicies.get("childLaborPolicy", False)
        
        discriminationPolicy = humanRightsPolicies.get("discriminationPolicy", False)
        
        forcedLaborPolicy = humanRightsPolicies.get("forcedLaborPolicy", False)
        
        hasOtherPolicies = humanRightsPolicies.get("hasOtherPolicies", False)
        
        hasComplaintsHandlingMechanism = humanRightsPolicies.get("hasComplaintsHandlingMechanism", False)
        
        humanTraffickingPolicy = humanRightsPolicies.get("humanTraffickingPolicy", False)
        
        accidentPreventionPolicy = humanRightsPolicies.get("accidentPreventionPolicy", False)
        
        otherPolicies = humanRightsPolicies.get("otherPolicies", "")
        
        self.builder.add_fact(
            "vsme:UndertakingHasACodeOfConductOrHumanRightsPolicyForItsOwnWorkforce",
            hasCodeOfConduct,
            unit=EFRAGTaxonomy()._unit("boolean"),
            decimals=0
        )
        
        self.builder.add_fact(
            "vsme:UndertakingHasAComplaintHandlingMechanismForItsOwnWorkforce",
            hasComplaintsHandlingMechanism,
            unit=EFRAGTaxonomy()._unit("boolean"),
            decimals=0
        )

        # Enumeration-set members must be encoded as a list of QName strings.
        selected_members = []

        if accidentPreventionPolicy:
            selected_members.append("vsme:AccidentPreventionMember")
        if childLaborPolicy:
            selected_members.append("vsme:ChildLabourMember")
        if discriminationPolicy:
            selected_members.append("vsme:DiscriminationMember")
        if forcedLaborPolicy:
            selected_members.append("vsme:ForcedLabourMember")
        if humanTraffickingPolicy:
            selected_members.append("vsme:HumanTraffickingMember")

        self.builder.add_fact(
            "vsme:TypeOfContentCoveredByTheCodeOfConductOrHumanRightsPolicyForItsOwnWorkforce",
            selected_members,
            decimals=None,
        )
        
        if hasOtherPolicies:
            self.builder.add_fact(
                "vsme:UndertakingHasOtherHumanRightsPoliciesForItsOwnWorkforce",
                hasOtherPolicies,
                unit=EFRAGTaxonomy()._unit("boolean"),
                decimals=0
            )
            
            self.builder.add_fact(
                "vsme:SpecificationOfOtherTypesOfContentCoveredByTheCodeOfConductOrHumanRightsPolicy",
                otherPolicies,
                decimals=None,
            )

    def map_serious_human_rights_incidents(self) -> None:
        incidents = self.form_social.get("seriousHumanRightsIncidents", {})
        
        hasValueChainIncidents = incidents.get("hasValueChainIncidents", False)
        
        childLabor = incidents.get("childLabor", False)
        
        discrimination = incidents.get("discrimination", False)
        
        forcedLabor = incidents.get("forcedLabor", False)
        
        humanTrafficking = incidents.get("humanTrafficking", False)
        
        other = incidents.get("other", False)
        
        descriptionOfActionsTaken = incidents.get("descriptionOfActionsTaken", None)
        
        selected_members = []
        if childLabor:
            selected_members.append("vsme:ChildLabourMember")
        if discrimination:
            selected_members.append("vsme:DiscriminationMember")
        if forcedLabor:
            selected_members.append("vsme:ForcedLabourMember")
        if humanTrafficking:
            selected_members.append("vsme:HumanTraffickingMember")
        if other:
            selected_members.append("vsme:OtherContentMember")
        
        self.builder.add_fact(
            "vsme:TypeOfHumanRightRelatedToTheConfirmedIncident",
            selected_members,
            decimals=None,
        )
        
        if other:
            self.builder.add_fact(
                "vsme:SpecificationOfOtherTypesOfConfirmedHumanRightsIncidents",
                incidents.get("otherMeasures", None),
                decimals=None,
            )
        
        
        self.builder.add_fact(
            "vsme:UndertakingIsAwareOfAnyConfirmedIncidentsInvolvingWorkersInTheValueChainAffectedCommunitiesConsumersAndEndUsers",
            hasValueChainIncidents,
            unit=EFRAGTaxonomy()._unit("boolean"),
            decimals=0
        )
        
        if descriptionOfActionsTaken:
            self.builder.add_fact(
                "vsme:DescriptionOfActionsTakeToAddressTheConfirmedIncidents",
                descriptionOfActionsTaken,
                decimals=0
            )
        

    def map_all(self) -> None:
        self.map_workforce()
        self.map_health_safety()
        self.map_additional_workforce_metrics()
        self.map_human_rights()
        self.map_serious_human_rights_incidents()
        self.mapCompensationCollectiveBargaining()