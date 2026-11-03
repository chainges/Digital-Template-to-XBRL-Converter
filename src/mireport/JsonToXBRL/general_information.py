"""Mapper functions for general and business information disclosures."""

from typing import Any, Dict

from mireport.JsonToXBRL.getNace import nace_to_member

from .common import EFRAGTaxonomy, SectionMapper, XBRLFactBuilder, ConfidentialAreas


def mapNaceCode (naceCode) -> str:
    if not naceCode:
        return ""
    return f"nace:{naceCode}" if not naceCode.startswith("nace:") else naceCode


class GeneralInformationMapper(SectionMapper):
    """Maps company information, reporting basis, and business model data."""

    def __init__(self, data: Dict[str, Any], builder: XBRLFactBuilder):
        super().__init__(data, builder)
        self.form_general = data.get("formGeneral", {})
        self.confidential_areas = data.get("confidentialAreas", [])
        self.organization = data.get("organization", {})

    def map_undertaking_legal_form(self) -> None:
        company_info = self.form_general.get("companyInfo", {})
        
        underTakingLegalForm = company_info.get("underTakingLegalForm")
        
        otherUndertakingsLegalForm = company_info.get("otherUndertakingsLegalForm")
        
        if underTakingLegalForm == "vsme:OtherUndertakingsLegalFormMember":
            self.builder.add_fact(
                concept="vsme:UndertakingsLegalForm",
                value="vsme:OtherUndertakingsLegalFormMember",
                decimals=None,
            )
                    
            self.builder.add_fact(
                concept="vsme:OtherUndertakingsLegalForm",
                value=otherUndertakingsLegalForm,
                decimals=None,
            )
        else:
            self.builder.add_fact(
                concept="vsme:UndertakingLegalForm",
                value=underTakingLegalForm,
                decimals=None,
            )
        
        return
    
    def map_basic_information(self) -> None:
        basic_information = self.form_general.get("basicModule", {})
        company_info = self.form_general.get("companyInfo", {})
        
        moduleScope = basic_information.get("moduleScope")
        
        self.builder.add_fact(
            concept="vsme:BasisForPreparation",
            value=moduleScope,
            decimals=None,
        )
        
        isConsolidated = company_info.get("isConsolidated")
        
        if isConsolidated:
            self.builder.add_fact(
                concept="vsme:BasisForReporting",
                value="vsme:ConsolidatedMember",
                decimals=None,
            )
        else:
            self.builder.add_fact(
                concept="vsme:BasisForReporting",
                value="vsme:IndividualMember",
                decimals=None,
            )
        
        containsPreviousPeriodDisclosures = basic_information.get("containsPreviousPeriodDisclosures")
        
        if containsPreviousPeriodDisclosures:
            self.builder.add_fact(
                concept="vsme:ReportContainsDisclosuresFromThePreviousReportingPeriodThatRemainUnchanged",
                value=containsPreviousPeriodDisclosures,
                unit=EFRAGTaxonomy()._unit("boolean"),
            )
            sectionsThatHasNotChanged = basic_information.get("sectionsThatHasNotChanged")
            if sectionsThatHasNotChanged:
                self.builder.add_fact(
                    concept="vsme:ListOfDisclosuresForWhichNoChangesAreReportedComparedToThePreviousPeriodReporting",
                    value=sectionsThatHasNotChanged,
                    decimals=None,
            )
            
            linkOfPreviousReport = basic_information.get("linkOfPreviousReport")
            if linkOfPreviousReport:
                self.builder.add_fact(
                    concept="vsme:LinkToPreviousReportContainingDisclosuresThatRemainUnchanged",
                    value=linkOfPreviousReport,
                    decimals=None,
                )
        else:
            self.builder.add_fact(
                concept="vsme:ReportContainsDisclosuresFromThePreviousReportingPeriodThatRemainUnchanged",
                value=False,
                unit=EFRAGTaxonomy()._unit("boolean"),
            )           
            
        return

    def map_subsidiaries(self) -> None:
        company_info = self.form_general.get("companyInfo", {})
        subsidiaries = company_info.get("subsidiaries")
        for idx, sub in enumerate(subsidiaries or [], start=1):
            name = sub.get("name")
            address = sub.get("address")
            # Fact 1: Name of the Subsidiary
            if name:
                self.builder.add_fact(
                    concept="vsme:NameOfTheSubsidiary",
                    value=name,
                    dimensions={
                        "dimension": "vsme:IdentifierOfSubsidiaryTypedAxis",
                        "typedValue": idx,
                    },
                )

            # Fact 2: Registered Address of the Subsidiary
            if address:
                self.builder.add_fact(
                    concept="vsme:RegisteredAddressOfTheSubsidiary",
                    value=address,
                    dimensions={
                        "dimension": "vsme:IdentifierOfSubsidiaryTypedAxis",
                        "typedValue": idx,
                    },
                )

    def map_sites(self) -> None:
        company_info = self.form_general.get("companyInfo", {})
        sites = company_info.get("properties")
        
        for idx, site in enumerate(sites or [], start=1):
            site_address = site.get("formattedAddress")
            site_postalCode = site.get("postalCode")
            site_city = site.get("city")
            site_country = f"country:{site.get('countryCode')}" if not site.get("countryCode", "").startswith("country:") else site.get("countryCode")
        
            

            # Fact 2: Address of the Site
            if site_address:
                self.builder.add_fact(
                    concept="vsme:AddressOfSite",
                    value=site_address,
                    dimensions={
                        "dimension": "vsme:IdentifierOfSiteTypedAxis",
                        "typedValue": idx,
                    },
                )
            
            self.builder.add_fact(
                concept="vsme:PostalCodeOfSite",
                value=site_postalCode,
                dimensions={
                    "dimension": "vsme:IdentifierOfSiteTypedAxis",
                    "typedValue": idx,
                },
            )
            
            self.builder.add_fact(
                concept="vsme:CityOfSite",
                value=site_city,
                dimensions={
                    "dimension": "vsme:IdentifierOfSiteTypedAxis",
                    "typedValue": idx,
                },
            )

            self.builder.add_fact(
                concept="vsme:CountryOfSite",
                value=site_country,
                dimensions={
                    "dimension": "vsme:IdentifierOfSiteTypedAxis",
                    "typedValue": idx,
                },
            )
            
        return

    def map_certifications(self) -> None:
        # TODO: Implement mapping of certifications
        pass
    
    def map_company_info(self) -> None:
        company_info = self.form_general.get("companyInfo", {})
        
        confidentialAreas = self.confidential_areas
        
        if len(confidentialAreas or []) > 0:
            self.builder.add_fact(
                concept="vsme:ListOfOmittedDisclosuresDeemedToBeClassifiedOrSensitiveInformation",
                value=confidentialAreas,
                decimals=None,
        )
            
        
        self.map_undertaking_legal_form()
        
        isConsolidated = company_info.get("isConsolidated")
        
        
        naceCode = company_info.get("naceCode")

        nace =  nace_to_member(naceCode)

        if naceCode:
            self.builder.add_fact(
                "vsme:NaceSectorClassificationCodes",
                value=[nace],
            )
        
        self.builder.add_fact(
            "vsme:Assets",
            company_info.get("balanceSheetTotal"),
            unit=EFRAGTaxonomy()._unit("EUR"),
            decimals=0
        )
        
        self.builder.add_fact(
            "vsme:Turnover",
            company_info.get("revenue"),
            unit=EFRAGTaxonomy()._unit("EUR"),
            decimals=0
        )
        
        # Headcount logic: Prefer headcount from social module if present
        total_employees = company_info.get("employees") or 100
        self.builder.add_fact(
            "vsme:NumberOfEmployees",
            total_employees,
            unit=EFRAGTaxonomy()._unit("count"),
            decimals=0
        )
        employeeCountingMethodology = company_info.get("EmployeeCountingMethodology") or "vsme:AtTheEndOfTheReportingPeriodMember"
        
        self.builder.add_fact(
            "vsme:EmployeeCountingMethodology",
            employeeCountingMethodology,
            decimals=None
        )

        typeOfEmployees = company_info.get("TypeOfNumberOfEmployees") or "vsme:HeadcountMember"

        self.builder.add_fact(
            "vsme:TypeOfNumberOfEmployees",
            typeOfEmployees,
            decimals=None
        )

        country = company_info.get("country") or "NO"

        country = f"country:{country}" if not country.startswith("country:") else country

        self.builder.add_fact(
            "vsme:CountryOfPrimaryOperationsAndLocationOfSignificantAssets",
            country,
            decimals=None
        )        
            
        if not "vsme:B1ListOfSubsidiariesMember" in confidentialAreas and isConsolidated:
            self.map_subsidiaries()
        
            
        if not "vsme:B1ListOfSitesMember" in confidentialAreas:
            self.map_sites()
        
        
        return

    def map_business_model(self) -> None:
        businessModel = self.form_general.get("businessModel")
        
        confidentialAreas = self.confidential_areas
        
        if not "vsme:C1-StrategyBusinessModelAndSustainabilityRelatedInitiativesMember" in confidentialAreas:
            # Map business model details here
            return
        
        businessRelationships = businessModel.get("businessRelationships") if businessModel else None
        markets = businessModel.get("markets") if businessModel else None
        productsAndServices = businessModel.get("productsAndServices") if businessModel else None
        sustainabilityStrategy = businessModel.get("sustainabilityStrategy") if businessModel else None
        
        if productsAndServices:
            self.builder.add_fact(
                concept="vsme:DescriptionOfSignificantGroupsOfProductsAndOrServicesOffered",
                value=productsAndServices,
                decimals=None,
            )

        if markets:
            self.builder.add_fact(
                concept="vsme:DescriptionOfSignificantMarketsTheUndertakingOperatesIn",
                value=markets,
                decimals=None,
            )

        if businessRelationships:
            self.builder.add_fact(
                concept="vsme:DescriptionOfMainBusinessRelationships",
                value=businessRelationships,
                decimals=None,
            )

        if sustainabilityStrategy:
            self.builder.add_fact(
                concept="vsme:DescriptionOfKeyElementsOfStrategyThatRelatesToOrAffectsSustainabilityIssues",
                value=sustainabilityStrategy,
                decimals=None,
            )
        return
        

    def map_sustainability_initiatives(self) -> None:
        sustainabilityInitiatives = self.form_general.get("sustainabilityInitiatives")
        confidentialAreas = self.confidential_areas
        
        hasSustainabilityPractices = sustainabilityInitiatives.get("hasSustainabilityPractices")
        
        # Skip mapping if the company does not have sustainability practices or if the relevant area is confidential.
        
        if not hasSustainabilityPractices or "vsme:B2-PracticesPoliciesAndFutureInitiativesForTransitioningTowardsAMoreSustainableEconomyMember" in confidentialAreas:
            return
        
        selectedSustainabilityIssueValues = sustainabilityInitiatives.get("selectedSustainabilityIssueValues")
        
        hasSetTargets = sustainabilityInitiatives.get("policiesHaveTargets")
        isPubliclyAvailable = sustainabilityInitiatives.get("arePracticesPubliclyAvailable")
        
        if selectedSustainabilityIssueValues and len(selectedSustainabilityIssueValues) > 0:
            self.builder.add_fact(
                concept="vsme:SustainabilityIssueAddressedByPracticePolicyAndOrFutureInitiative",
                value=selectedSustainabilityIssueValues,
                decimals=None,
            )
        
        
        self.builder.add_fact(
            concept="vsme:UndertakingHasSetATargetWhichIsRelatedToAPolicy",
            value=hasSetTargets,
            decimals=None,
        )

        self.builder.add_fact(
            concept="vsme:PracticePolicyAndOrFutureInitiativeIsPubliclyAvailable",
            value=isPubliclyAvailable,
            decimals=None,
        )
        
        ### if the description of practices, policies, and future initiatives is confidential then skip mapping it
        
        if "vsme:C2-DescriptionOfPracticesPoliciesAndFutureInitiativesForTransitioningTowardsAMoreSustainableEconomyMember" in confidentialAreas:
            return
        
        descriptionOfPracticesPolicies = self.form_general.get("descriptionOfPracticesPolicies")
        
        
        
        c2_accountable_role_or_person = self.form_general.get("c2_accountable_role_or_person")
        
        
        c2_sustainability_practice_description = descriptionOfPracticesPolicies.get("c2_sustainability_practice_description") if descriptionOfPracticesPolicies else None
        c2_monitoring_targets_description = descriptionOfPracticesPolicies.get("c2_monitoring_targets_description") if descriptionOfPracticesPolicies else None

        if c2_sustainability_practice_description:
            self.builder.add_fact(
                concept="vsme:DescriptionOfPracticesPoliciesAndOrFutureInitiatives",
                value=c2_sustainability_practice_description,
                decimals=None,
            )

        if c2_monitoring_targets_description:
            self.builder.add_fact(
                concept="vsme:DescriptionOfATargetRelatedToAPolicy",
                value=c2_monitoring_targets_description,
                decimals=None,
            )

        if c2_accountable_role_or_person:
            self.builder.add_fact(
                concept="vsme:MostSeniorLevelAccountableForImplementationOfPolicies",
                value=c2_accountable_role_or_person,
                decimals=None,
            )
        
        return

    def map_all(self) -> None:
        self.map_basic_information()
        self.map_company_info()
        self.map_business_model()
        self.map_sustainability_initiatives()