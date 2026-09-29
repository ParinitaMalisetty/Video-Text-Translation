import json
import logging
from typing import List, Optional
from app.modules.base import BaseTranslationModule, TranscriptSegment
from app.config import settings

logger = logging.getLogger(__name__)

# Fallback translations for standard demo segments
DEMO_TELUGU_TRANSLATIONS = {
    1: "ఆటోమేటెడ్ వీడియో అనువాదం యొక్క ఈ ప్రదర్శనకు స్వాగతం.",
    2: "ఈ ప్రాజెక్ట్‌లో, ఇంగ్లీష్ ఆడియోను లిప్యంతరీకరించడం మరియు భారతీయ భాషల్లోకి అనువదించడం జరుగుతుంది.",
    3: "మాడ్యూల్ ఒకటి ప్రసంగాన్ని తెలుగులోకి అనువదిస్తుంది, మరియు మాడ్యూల్ రెండు ప్రసంగాన్ని హిందీలోకి అనువదిస్తుంది.",
    4: "ఖచ్చితమైన ఉపశీర్షికలు మరియు సహజ వాయిస్ డబ్బింగ్ సజావుగా సృష్టించబడతాయి."
}

class TeluguTranslationModule(BaseTranslationModule):
    """Module 1: Translates English transcript segments into Telugu."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Gemini Client for Telugu Module: {e}")

    @property
    def language_code(self) -> str:
        return "te"

    @property
    def language_name(self) -> str:
        return "Telugu"

    async def translate_segments(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """Translates each English segment into Telugu, keeping timing intact."""
        if not segments:
            return []

        if self.client:
            return await self._translate_with_gemini(segments)

        return self._fallback_translate(segments)

    async def _translate_with_gemini(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        from google.genai import types

        logger.info(f"Translating {len(segments)} segments to Telugu using Gemini...")
        input_data = [seg.model_dump() for seg in segments]

        prompt = (
            "You are an expert English-to-Telugu translator. "
            "Translate the following English subtitle segments into natural, spoken Telugu script. "
            "Maintain the exact same 'id', 'start', and 'end' timing values. "
            "Only translate the 'text' field into fluent Telugu script. "
            "Return ONLY a valid JSON array of objects with keys: id, start, end, text.\n\n"
            f"Input Segments:\n{json.dumps(input_data, ensure_ascii=False)}"
        )

        candidate_models = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3-flash-preview"]
        last_error = None

        for model_name in candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                data = json.loads(raw_text.strip())

                return [
                    TranscriptSegment(
                        id=item["id"],
                        start=float(item["start"]),
                        end=float(item["end"]),
                        text=str(item["text"]).strip()
                    )
                    for item in data
                ]
            except Exception as e:
                last_error = e
                logger.warning(f"Telugu translation with {model_name} failed: {e}. Trying next model...")

        logger.warning(f"All Gemini models failed for Telugu translation: {last_error}. Switching to MyMemory translator...")
        return self._fallback_translate(segments)

    def _fallback_translate(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        logger.info(f"Using MyMemoryTranslator for {len(segments)} Telugu segments...")
        try:
            from deep_translator import MyMemoryTranslator
            translator = MyMemoryTranslator(source="en-GB", target="te-IN")
            results = []
            for seg in segments:
                translated_text = translator.translate(seg.text)
                results.append(
                    TranscriptSegment(
                        id=seg.id,
                        start=seg.start,
                        end=seg.end,
                        text=translated_text or seg.text
                    )
                )
            return results
        except Exception as e:
            logger.error(f"MyMemory Telugu translation failed: {e}")
            return segments
