import logging
from pathlib import Path
from typing import List, Optional
import edge_tts
from app.modules.base import TranscriptSegment
from app.config import settings

logger = logging.getLogger(__name__)

VOICE_MAP = {
    "te": {
        "female": "te-IN-ShrutiNeural",
        "male": "te-IN-MohanNeural",
    },
    "hi": {
        "female": "hi-IN-SwaraNeural",
        "male": "hi-IN-MadhurNeural",
    }
}

class TTSService:
    """Generates natural neural audio speech for Telugu and Hindi using Edge-TTS."""
    
    @staticmethod
    def get_voice(language_code: str, gender: str = "female") -> str:
        lang_voices = VOICE_MAP.get(language_code.lower())
        if lang_voices:
            return lang_voices.get(gender.lower(), list(lang_voices.values())[0])
        return "te-IN-ShrutiNeural" if language_code.lower() == "te" else "hi-IN-SwaraNeural"

    async def generate_speech(self, text: str, output_path: Path, voice: Optional[str] = None) -> Path:
        """Synthesize given text into an MP3 audio file."""
        if not text.strip():
            raise ValueError("Text cannot be empty for speech synthesis.")
            
        voice = voice or settings.TELUGU_VOICE
        logger.info(f"Synthesizing speech with voice: {voice}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        communicate = edge_tts.Communicate(text=text, voice=voice)
        await communicate.save(str(output_path))
        return output_path

    async def generate_audio_for_translation(
        self,
        segments: List[TranscriptSegment],
        language_code: str,
        output_path: Path,
        gender: str = "female"
    ) -> Path:
        """
        Synthesizes full text from translated segments into a unified audio stream.
        """
        combined_text = " ".join([seg.text.strip() for seg in segments if seg.text.strip()])
        voice = self.get_voice(language_code, gender)
        return await self.generate_speech(text=combined_text, output_path=output_path, voice=voice)
