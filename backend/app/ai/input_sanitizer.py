from backend.app.schemas.base import EvidenceItem, EvidenceGap

def sanitize_evidence_for_llm(evidence_items: list[EvidenceItem], gaps: list[EvidenceGap]) -> dict:
    """
    Sanitize evidence objects before passing to generative AI.
    Strictly strips:
    - Place names, business entities, photos, merchant titles
    - User notes, free text, PII
    Retains ONLY derived, structured numeric and categorical metrics.
    """
    sanitized_items = []
    for item in evidence_items:
        sanitized_items.append({
            "evidence_id": item.id,
            "module": item.module,
            "metric": item.metric,
            "value": item.value,
            "unit": item.unit,
            "radius_m": item.radius_m,
            "result_cap_reached": item.result_cap_reached,
            "provenance_kind": item.provenance_kind,
            "granularity": item.granularity,
            "status": "available" if item.value is not None else "limited"
        })

    sanitized_gaps = []
    for gap in gaps:
        sanitized_gaps.append({
            "gap_id": f"gap:{gap.module}",
            "module": gap.module,
            "reason": gap.reason,
            "granularity_needed": gap.granularity_needed
        })

    return {
        "evidence_facts": sanitized_items,
        "data_gaps": sanitized_gaps
    }
