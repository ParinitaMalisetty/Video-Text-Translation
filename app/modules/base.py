from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field

class TranscriptSegment(BaseModel):
    id: int
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed or translated text")

class TranslationResult(BaseModel):
    language_code: str
    language_name: str
    full_text: str
    segments: List[TranscriptSegment]
    srt_file: Optional[str] = None
    vtt_file: Optional[str] = None
    audio_file: Optional[str] = None

class VideoTranslationResponse(BaseModel):
    job_id: str
    video_filename: str
    duration_seconds: Optional[float] = None
    english_transcript: TranslationResult
    telugu_translation: Optional[TranslationResult] = None
    hindi_translation: Optional[TranslationResult] = None
    dubbed_video_telugu: Optional[str] = None
    dubbed_video_hindi: Optional[str] = None

class BaseTranslationModule(ABC):
    """Abstract interface for language translation modules."""
    
    @property
    @abstractmethod
    def language_code(self) -> str:
        """e.g. 'te' for Telugu, 'hi' for Hindi"""
        pass
        
    @property
    @abstractmethod
    def language_name(self) -> str:
        """e.g. 'Telugu', 'Hindi'"""
        pass

    @abstractmethod
    async def translate_segments(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """Translates a list of timestamped segments preserving time boundaries."""
        pass
