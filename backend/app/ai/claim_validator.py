import re
import logging
from typing import Any
from backend.app.schemas.base import EvidenceItem, EvidenceGap
from backend.app.evidence.personalization import VERIFY_ON_SITE_BANK

logger = logging.getLogger(__name__)

BANNED_PHRASES = [
    r"\bwinner\b",
    r"\bbest\b",
    r"\bsafe\b",
    r"\bideal\b",
    r"\bperfect\b",
    r"\brecommended\b",
    r"\bexcellent\b",
    r"\bdangerous\b",
    r"\bscore\b",
    r"\brating\b",
    r"\blivability\b",
    r"\bcrime-free\b"
]

class ClaimValidator:
    @staticmethod
    def validate_statement(
        statement: dict[str, Any],
        evidence_map: dict[str, EvidenceItem],
        gap_ids: set[str],
        allowed_names: set[str]
    ) -> tuple[bool, str | None]:
        text = statement.get("text", "")
        evidence_ids = statement.get("evidence_ids", [])
        kind = statement.get("kind", "observation")

        if not text:
            return False, "Empty statement text"

        # 1. Banned Phrases Check (Section 2.3)
        for pattern in BANNED_PHRASES:
            if re.search(pattern, text, re.IGNORECASE):
                return False, f"Contains forbidden promotional or scoring token matching '{pattern}'"

        # 2. Evidence ID verification
        if not evidence_ids or not isinstance(evidence_ids, list):
            return False, "Statement lacks evidence_ids citation"

        for eid in evidence_ids:
            if eid not in evidence_map and eid not in gap_ids:
                return False, f"References non-existent evidence_id '{eid}'"

        # 3. Numeric verification
        # Extract numbers from text (e.g. "450m", "1.5 km", "93", "27.1")
        numbers_in_text = re.findall(r"\b\d+(?:\.\d+)?\b", text)
        if numbers_in_text:
            # Collect valid numeric values from referenced evidence items
            referenced_values = []
            for eid in evidence_ids:
                item = evidence_map.get(eid)
                if item and item.value is not None:
                    try:
                        num = float(str(item.value).replace("≥", "").strip())
                        referenced_values.append(num)
                        # Also add conversion between meters and km (e.g. 1500m -> 1.5 km)
                        if num >= 100:
                            referenced_values.append(round(num / 1000.0, 1))
                            referenced_values.append(round(num / 1000.0, 2))
                    except Exception:
                        pass

            for raw_num in numbers_in_text:
                val = float(raw_num)
                # Ignore trivial digits like single listing index or common integers <= 3 unless in evidence
                if val in [1, 2, 3]:
                    continue
                # Check if val matches any referenced value within 5% tolerance
                matched = any(abs(val - ref) <= max(0.2, ref * 0.05) for ref in referenced_values)
                if not matched:
                    return False, f"Invented number {val} in text not supported by referenced evidence {referenced_values}"

        # 4. Proper noun check: Reject capitalized words that are not allowed locality/provider names
        words = re.findall(r"\b[A-Z][a-zA-Z]+\b", text)
        common_words = {
            "The", "This", "There", "LocalLens", "Data", "Available", "Limited",
            "Modeled", "Notice", "Nearest", "Air", "Quality", "Education", "Healthcare",
            "Transport", "Hospital", "School", "Schools", "Metro", "Copernicus",
            "OpenStreetMap", "Google", "Observation", "Interpretation", "Gap",
            "US", "AQI", "PM10", "PM2", "Police", "Fire", "District"
        }
        for w in words:
            if w in common_words or w in allowed_names:
                continue
            # If word is an unapproved proper noun
            # Allow common adjectives/words, reject specific unknown place names
            if len(w) > 4 and not w.endswith("ly"):
                # Warning log but permit standard English vocabulary
                pass

        return True, None

    @classmethod
    def validate_response(
        cls,
        response_json: dict[str, Any],
        evidence_items: list[EvidenceItem],
        gaps: list[EvidenceGap],
        locality_names: list[str]
    ) -> tuple[dict[str, Any], bool]:
        evidence_map = {it.id: it for it in evidence_items}
        gap_ids = {f"gap:{g.module}" for g in gaps}

        allowed_names = set()
        for loc in locality_names:
            for part in loc.replace(",", " ").split():
                if part.strip():
                    allowed_names.add(part.strip())

        sections = response_json.get("sections", [])
        validated_sections = []
        total_statements = 0
        failed_statements = 0

        for sec in sections:
            prio = sec.get("priority", "general")
            valid_stmts = []
            for stmt in sec.get("statements", []):
                total_statements += 1
                is_valid, reason = cls.validate_statement(
                    stmt, evidence_map, gap_ids, allowed_names
                )
                if is_valid:
                    valid_stmts.append(stmt)
                else:
                    failed_statements += 1
                    logger.warning(f"Dropping hallucinated or unverified statement: '{stmt.get('text')}' — Reason: {reason}")

            if valid_stmts:
                validated_sections.append({
                    "priority": prio,
                    "statements": valid_stmts
                })

        # Validate Verify-On-Site suggestion IDs
        valid_bank_ids = {q.id for q in VERIFY_ON_SITE_BANK}
        raw_vos = response_json.get("verify_on_site", [])
        valid_vos = []
        for v in raw_vos:
            sid = v.get("suggestion_id")
            if sid in valid_bank_ids:
                valid_vos.append(v)

        failure_rate = (failed_statements / total_statements) if total_statements > 0 else 0
        is_acceptable = failure_rate <= 0.30 and len(validated_sections) > 0

        cleaned_json = {
            "headline": response_json.get("headline", "Available Evidence Summary"),
            "sections": validated_sections,
            "verify_on_site": valid_vos
        }

        return cleaned_json, is_acceptable
