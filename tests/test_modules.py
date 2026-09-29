import pytest
from app.modules import (
    TranscriptSegment,
    TeluguTranslationModule,
    HindiTranslationModule,
    TTSService
)

@pytest.mark.asyncio
async def test_telugu_module():
    mod = TeluguTranslationModule()
    assert mod.language_code == "te"
    assert mod.language_name == "Telugu"

    segments = [
        TranscriptSegment(id=1, start=0.0, end=3.5, text="Welcome to this video demonstration."),
        TranscriptSegment(id=2, start=3.8, end=7.0, text="In this project, English audio is translated.")
    ]
    translated = await mod.translate_segments(segments)
    assert len(translated) == 2
    assert translated[0].id == 1
    assert translated[0].start == 0.0
    assert translated[0].end == 3.5
    assert len(translated[0].text) > 0

@pytest.mark.asyncio
async def test_hindi_module():
    mod = HindiTranslationModule()
    assert mod.language_code == "hi"
    assert mod.language_name == "Hindi"

    segments = [
        TranscriptSegment(id=1, start=0.0, end=3.5, text="Welcome to this video demonstration.")
    ]
    translated = await mod.translate_segments(segments)
    assert len(translated) == 1
    assert translated[0].id == 1
    assert len(translated[0].text) > 0

def test_tts_voice_mapping():
    assert TTSService.get_voice("te", "female") == "te-IN-ShrutiNeural"
    assert TTSService.get_voice("te", "male") == "te-IN-MohanNeural"
    assert TTSService.get_voice("hi", "female") == "hi-IN-SwaraNeural"
    assert TTSService.get_voice("hi", "male") == "hi-IN-MadhurNeural"
