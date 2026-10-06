import json
import logging
from typing import Any
from backend.app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the LocalLens Evidence Synthesis Engine.
Your task is to synthesize structured evidence facts for a neighborhood into a coherent, priority-ordered JSON summary.

CRITICAL RULES:
1. Output ONLY valid JSON matching this schema:
{
  "headline": "<1-sentence summary of evidence depth>",
  "sections": [
    {
      "priority": "<priority_name>",
      "statements": [
        {
          "text": "<concise observation or interpretation>",
          "kind": "observation" | "interpretation" | "gap",
          "evidence_ids": ["<exact_evidence_id_from_input>"]
        }
      ]
    }
  ],
  "verify_on_site": [
    { "suggestion_id": "<exact_id_from_provided_list>" }
  ]
}

2. ZERO FABRICATION:
- NEVER invent places, merchant names, addresses, numbers, distances, or ratings.
- Every number in your text MUST match a referenced evidence item's value.
- NEVER invent new proper nouns or place names.

3. FORBIDDEN OUTPUT (STRICT):
- Do NOT use: "winner", "best", "safe", "ideal", "perfect", "recommended", "excellent", "dangerous", "score", "rating".
- Do NOT output any composite locality score.
- Label trade-offs neutrally.

4. If available evidence is sparse or insufficient, output: "There is not enough available data to make a stronger observation."
"""

class LLMService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.model_name = settings.LLM_MODEL
        self.gemini_key = settings.GEMINI_API_KEY
        self.anthropic_key = settings.ANTHROPIC_API_KEY

    async def generate_summary(self, user_prompt: str) -> dict[str, Any] | None:
        if not settings.FEATURE_AI:
            logger.info("FEATURE_AI is disabled. Returning None to trigger fallback.")
            return None

        # 1. Try Gemini
        if self.provider == "gemini" and self.gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=SYSTEM_PROMPT
                )
                response = model.generate_content(
                    user_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        response_mime_type="application/json"
                    )
                )
                if response and response.text:
                    return json.loads(response.text)
            except Exception as e:
                logger.error(f"Gemini generation error: {e}")
                return None

        # 2. Try Anthropic if configured
        if self.provider == "anthropic" and self.anthropic_key:
            try:
                import httpx
                headers = {
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                body = {
                    "model": self.model_name,
                    "max_tokens": 1000,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_prompt}]
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post("https://api.anthropic.com/v1/messages", json=body, headers=headers)
                    if resp.status_code == 200:
                        content_block = resp.json().get("content", [])[0]
                        return json.loads(content_block.get("text", "{}"))
            except Exception as e:
                logger.error(f"Anthropic generation error: {e}")
                return None

        return None
