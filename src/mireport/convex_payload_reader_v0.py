from __future__ import annotations

from datetime import date
from typing import Any

from mireport.conversionresults import ConversionResultsBuilder, MessageType, Severity
from mireport.exceptions import InlineReportException
from mireport.localise import get_locale_from_str
from mireport.report import InlineReport
from mireport.taxonomy import Concept, getTaxonomy, listTaxonomies


def _read_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _resolve_entity_scheme(raw_scheme: str, defaults: dict[str, Any]) -> str:
    key = raw_scheme.strip().replace(" ", "").lower()
    known = defaults.get("entityIdentifierLabelsToSchemes", {})
    if isinstance(known, dict) and key in known:
        return str(known[key])
    return raw_scheme.strip()


def _resolve_concept(
    report: InlineReport, text: str, *, only_reportable: bool = True
) -> Concept | None:
    return report.taxonomy.resolveConcept(
        text,
        by_label=False,
        by_name=True,
        by_qname=True,
        only_reportable=only_reportable,
    )


def _parse_decimals(raw: Any) -> int | str:
    if raw is None:
        return "INF"
    if isinstance(raw, int):
        return raw
    s = str(raw).strip().upper()
    if s == "INF":
        return "INF"
    return int(s)


def _parse_numeric_value(raw: Any) -> int | float:
    if isinstance(raw, bool):
        raise ValueError("Booleans are not valid numeric fact values")
    if isinstance(raw, (int, float)):
        return raw
    s = str(raw).strip()
    if not s:
        raise ValueError("Empty numeric value")
    if any(ch in s for ch in (".", "e", "E")):
        return float(s)
    return int(s)


def _parse_period_boundary(raw: str) -> date:
    value = raw.strip()
    if "T" in value:
        value = value.split("T", 1)[0]
    return date.fromisoformat(value)


def _normalise_dimensions(raw: Any) -> list[dict[str, Any]]:
    """Accept both legacy list format and mapper dict format for dimensions."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [d for d in raw if isinstance(d, dict)]
    if isinstance(raw, dict):
        if "dimension" in raw and "member" in raw:
            dimension = str(raw.get("dimension", "")).strip()
            member = str(raw.get("member", "")).strip()
            if dimension and member:
                return [{"dimension": dimension, "member": member}]
        dims: list[dict[str, Any]] = []
        for dimension_name, member_name in raw.items():
            dims.append(
                {
                    "dimension": str(dimension_name),
                    "member": str(member_name),
                }
            )
        return dims
    raise ValueError("dimensions must be an array or object when provided")


def _resolve_or_create_named_period(
    report: InlineReport,
    raw_period: str,
    default_start: date,
    default_end: date,
    period_cache: dict[tuple[date, date], str],
) -> str:
    """Resolve named periods and support interval strings like YYYY-MM-DDT00:00:00/YYYY-MM-DDT00:00:00."""
    period_name = raw_period.strip()
    if not period_name:
        return "cur"

    if report.hasNamedPeriod(period_name):
        return period_name

    if "/" not in period_name:
        raise InlineReportException(f"Period '{period_name}' does not exist in the report.")

    start_raw, end_raw = period_name.split("/", 1)
    start_date = _parse_period_boundary(start_raw)
    end_date = _parse_period_boundary(end_raw)
    if start_date > end_date:
        raise InlineReportException(
            f"Invalid period '{period_name}': start date is after end date."
        )

    if (start_date, end_date) == (default_start, default_end):
        return "cur"

    existing_name = period_cache.get((start_date, end_date))
    if existing_name:
        return existing_name

    new_name = f"p{len(period_cache) + 1}"
    report.addDurationPeriod(new_name, start_date, end_date)
    period_cache[(start_date, end_date)] = new_name
    return new_name


def _safe_simple_unit(report: InlineReport, concept: Concept, raw_unit: str) -> Any:
    """Build a unit QName and fall back to xbrli:pure for unsupported mapper units."""
    unit_text = raw_unit.strip()
    if not unit_text:
        return report.taxonomy.QNameMaker.fromString("xbrli:pure")

    try:
        qname = report.taxonomy.QNameMaker.fromString(unit_text)
        # Trigger UTR lookup early to avoid render-time crashes on unknown units.
        report.taxonomy.UTR.getSymbolForUnit(qname, concept.dataType)
        return qname
    except Exception:
        return report.taxonomy.QNameMaker.fromString("xbrli:pure")


def _apply_dimension(
    report: InlineReport,
    fact_builder: Any,
    dimension_spec: dict[str, Any],
) -> None:
    dimension_text = str(dimension_spec.get("dimension", "")).strip()
    if not dimension_text:
        raise InlineReportException("Dimension is required when setting dimensions.")

    dimension = _resolve_concept(report, dimension_text, only_reportable=False)
    if dimension is None:
        raise InlineReportException(f"Unknown dimension: {dimension_text}")

    typed_value = dimension_spec.get("typedValue")
    member_text = str(dimension_spec.get("member", "")).strip()

    if typed_value is not None:
        fact_builder.setTypedDimension(dimension, typed_value)
        return

    if not member_text:
        raise InlineReportException(
            f"Member is required for explicit dimension {dimension_text}."
        )

    member = _resolve_concept(report, member_text, only_reportable=False)
    if member is None:
        raise InlineReportException(f"Unknown dimension member: {member_text}")

    fact_builder.setExplicitDimension(dimension, member)


def build_report_from_convex_payload(
    payload: dict[str, Any],
    results_builder: ConversionResultsBuilder,
    defaults: dict[str, Any],
) -> InlineReport:
    meta = _read_dict(payload, "meta")
    entity = _read_dict(meta, "entity")
    reporting_period = _read_dict(meta, "reportingPeriod")

    entry_point = str(meta.get("taxonomyEntryPoint", "")).strip()
    if not entry_point:
        taxonomy_defaults = _read_dict(defaults, "taxonomyEntryPoints")
        entry_point = str(taxonomy_defaults.get("supportedEntryPoint", "")).strip()

    supported_entry_points = set(listTaxonomies())
    if not entry_point:
        raise ValueError("meta.taxonomyEntryPoint is required.")
    if entry_point not in supported_entry_points:
        raise ValueError(
            "Unsupported taxonomy entry point. "
            f"Provided: {entry_point}. Supported: {sorted(supported_entry_points)}"
        )

    locale = get_locale_from_str(str(meta.get("reportingLanguage", "")))
    report = InlineReport(getTaxonomy(entry_point), locale)
    report.addSchemaRef(entry_point)

    entity_name = str(entity.get("name", "")).strip()
    if not entity_name:
        raise ValueError("meta.entity.name is required.")
    report.setEntityName(entity_name)

    entity_identifier = str(entity.get("identifier", "")).strip()
    if not entity_identifier:
        raise ValueError("meta.entity.identifier is required.")
    report.setDefaultAspect("entity-identifier", entity_identifier)

    raw_scheme = str(entity.get("identifierScheme", "")).strip()
    if not raw_scheme:
        raise ValueError("meta.entity.identifierScheme is required.")
    report.setDefaultAspect("entity-scheme", _resolve_entity_scheme(raw_scheme, defaults))

    currency = str(meta.get("currency", "EUR")).strip().upper()
    if not currency:
        currency = "EUR"
    report.setDefaultAspect("monetary-units", currency)

    start_raw = str(reporting_period.get("startDate", "")).strip()
    end_raw = str(reporting_period.get("endDate", "")).strip()
    if not (start_raw and end_raw):
        raise ValueError("meta.reportingPeriod.startDate and endDate are required.")

    start_date = date.fromisoformat(start_raw)
    end_date = date.fromisoformat(end_raw)
    if start_date > end_date:
        raise ValueError("Reporting period startDate cannot be after endDate.")

    report.addDurationPeriod("cur", start_date, end_date)
    report.setDefaultPeriodName("cur")

    report_title = str(meta.get("reportTitle", "")).strip()
    if report_title:
        report.setReportTitle(report_title)
    report_subtitle = str(meta.get("reportSubtitle", "")).strip()
    if report_subtitle:
        report.setReportSubtitle(report_subtitle)

    facts = payload.get("facts")
    if not isinstance(facts, list):
        raise ValueError("facts must be an array.")

    global_dimensions = _normalise_dimensions(payload.get("dimensions", []))

    period_cache: dict[tuple[date, date], str] = {(start_date, end_date): "cur"}

    added_facts = 0
    for index, raw_fact in enumerate(facts, start=1):
        if not isinstance(raw_fact, dict):
            results_builder.addMessage(
                f"Skipping fact at index {index}: object expected.",
                Severity.ERROR,
                MessageType.Conversion,
            )
            continue

        concept_text = str(raw_fact.get("concept", "")).strip()
        if not concept_text:
            results_builder.addMessage(
                f"Skipping fact at index {index}: concept is required.",
                Severity.ERROR,
                MessageType.Conversion,
            )
            continue

        concept = _resolve_concept(report, concept_text)
        if concept is None:
            results_builder.addMessage(
                f"Skipping fact at index {index}: unknown concept '{concept_text}'.",
                Severity.ERROR,
                MessageType.Conversion,
            )
            continue

        try:
            value = raw_fact.get("value")
            if value is None:
                raise ValueError("value is required")

            if concept.isNumeric:
                value = _parse_numeric_value(value)

            period_name = _resolve_or_create_named_period(
                report,
                str(raw_fact.get("period", "cur")),
                start_date,
                end_date,
                period_cache,
            )
            fact_builder = report.getFactBuilder().setConcept(concept).setValue(
                value
            ).setNamedPeriod(period_name)

            if concept.isNumeric:
                if concept.isMonetary:
                    unit_text = str(raw_fact.get("unit", currency)).strip()
                    if unit_text.lower().startswith("iso4217:"):
                        unit_text = unit_text.split(":", 1)[1]
                    fact_builder.setCurrency(unit_text)
                else:
                    unit_text = str(raw_fact.get("unit", "")).strip()
                    if "/" in unit_text:
                        numerator, denominator = unit_text.split("/", 1)
                        numerator_q = report.taxonomy.QNameMaker.fromString(
                            numerator.strip()
                        )
                        denominator_q = report.taxonomy.QNameMaker.fromString(
                            denominator.strip()
                        )
                        fact_builder.setComplexUnit(numerator_q, denominator_q)
                    else:
                        fact_builder.setSimpleUnit(
                            _safe_simple_unit(report, concept, unit_text)
                        )

                    fact_builder.setDecimals(_parse_decimals(raw_fact.get("decimals")))

            local_dimensions = _normalise_dimensions(raw_fact.get("dimensions", []))

            for dim in global_dimensions:
                if not isinstance(dim, dict):
                    continue
                _apply_dimension(report, fact_builder, dim)

            for dim in local_dimensions:
                if not isinstance(dim, dict):
                    continue
                _apply_dimension(report, fact_builder, dim)

            report.addFact(fact_builder.buildFact())
            added_facts += 1
        except Exception as exc:
            results_builder.addMessage(
                f"Skipping fact at index {index} concept '{concept_text}': {exc}",
                Severity.ERROR,
                MessageType.Conversion,
                taxonomy_concept=concept,
            )

    if added_facts == 0:
        raise ValueError("No valid facts were provided in payload.")

    results_builder.addMessage(
        f"JSON payload parsed and {added_facts} fact(s) added to report.",
        Severity.INFO,
        MessageType.Conversion,
    )
    return report
