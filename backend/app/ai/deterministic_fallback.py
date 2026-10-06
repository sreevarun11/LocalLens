from typing import Any
from backend.app.schemas.base import EvidenceItem, EvidenceGap
from backend.app.evidence.personalization import Finding, PriorityGapCallout, VerifyOnSiteQuestion

def generate_deterministic_synthesis(
    locality_name: str,
    findings: list[Finding],
    gaps: list[EvidenceGap],
    verify_questions: list[VerifyOnSiteQuestion]
) -> dict[str, Any]:
    """
    Deterministic synthesis fallback that guarantees a 100% compliant, validated JSON summary
    whenever the LLM API key is unconfigured, times out, or fails ClaimValidator checks.
    """
    sections = []

    for f in findings:
        statements = []

        # Observation statement directly grounded in finding
        statements.append({
            "text": f.detail,
            "kind": "observation",
            "evidence_ids": f.evidence_ids
        })

        # Interpretation statement for distance preferences
        if f.within_preference == "yes":
            statements.append({
                "text": f"The nearest facility meets your preferred distance threshold.",
                "kind": "interpretation",
                "evidence_ids": f.evidence_ids
            })
        elif f.within_preference == "no":
            statements.append({
                "text": "The nearest facility identified in this map database is farther than your preferred distance threshold.",
                "kind": "interpretation",
                "evidence_ids": f.evidence_ids
            })

        sections.append({
            "priority": f.priority,
            "statements": statements
        })

    # Add Gap section
    gap_statements = []
    for g in gaps:
        gap_statements.append({
            "text": f"{g.module.capitalize()} data limitation: {g.reason}",
            "kind": "gap",
            "evidence_ids": [f"gap:{g.module}"]
        })

    if gap_statements:
        sections.append({
            "priority": "data_coverage_gaps",
            "statements": gap_statements
        })

    vos_list = [{"suggestion_id": q.id} for q in verify_questions[:4]]

    return {
        "headline": f"Evidence Summary for {locality_name}",
        "sections": sections,
        "verify_on_site": vos_list,
        "mode": "deterministic_fallback"
    }
