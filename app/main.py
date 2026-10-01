import uuid
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.core.media_processor import MediaProcessor
from app.modules import (
    ASRService,
    TeluguTranslationModule,
    HindiTranslationModule,
    TTSService,
    TranslationResult,
    VideoTranslationResponse
)
from app.utils.subtitle_utils import save_subtitles

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("video_translator")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI service to transcribe English video audio and translate into Telugu (Module 1) and Hindi (Module 2) with subtitles and voiceover dubbing."
)

# CORS middleware
allowed_origins = [
    origin.strip()
    for origin in settings.ALLOWED_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static and output files
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/outputs", StaticFiles(directory=str(settings.OUTPUT_DIR)), name="outputs")

media_processor = MediaProcessor()
tts_service = TTSService()

@app.get("/")
async def root():
    """Serves the interactive web UI dashboard."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": f"Welcome to {settings.APP_NAME}. Visit /docs for Swagger API documentation."}


@app.get("/api/v1/health")
async def health_check():
    """Returns system status, active modules, and environment readiness."""
    return {
        "status": "online",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "modules": {
            "module_1": {"name": "Telugu Translation Engine", "code": "te"},
            "module_2": {"name": "Hindi Translation Engine", "code": "hi"},
            "tts_dubbing": {"status": "available", "engine": "Edge-TTS Neural"}
        },
        "gemini_api_configured": bool(settings.GEMINI_API_KEY),
        "ffmpeg_status": "ready (bundled)"
    }
async def save_uploaded_video(file: UploadFile, destination: Path) -> None:
    """Validate and safely save an uploaded video within the configured size limit."""

    filename = file.filename or ""
    extension = Path(filename).suffix.lower()

    allowed_extensions = {
        ext.strip().lower()
        for ext in settings.ALLOWED_VIDEO_EXTENSIONS.split(",")
        if ext.strip()
    }

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported video format. Allowed formats: MP4, MKV, MOV, WebM.",
        )

    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total_size = 0
    chunk_size = 1024 * 1024

    try:
        with open(destination, "wb") as buffer:
            while chunk := await file.read(chunk_size):
                total_size += len(chunk)

                if total_size > max_size:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"Video file is too large. "
                            f"Maximum allowed size is {settings.MAX_UPLOAD_SIZE_MB} MB."
                        ),
                    )

                buffer.write(chunk)

    except HTTPException:
        if destination.exists():
            destination.unlink()
        raise
    except Exception:
        if destination.exists():
            destination.unlink()
        raise
    finally:
        await file.close()
async def _process_pipeline(
    file: UploadFile,
    languages: str,
    generate_subtitles: bool,
    generate_dubbing: bool,
    voice_gender: str,
    api_key_override: Optional[str]
) -> VideoTranslationResponse:
    job_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename or "").suffix.lower()
    saved_video_path = settings.UPLOAD_DIR / f"{job_id}{ext}"

    logger.info(f"[{job_id}] Saving uploaded video {file.filename}...")

    await save_uploaded_video(file, saved_video_path)

    # 2. Extract audio
    logger.info(f"[{job_id}] Extracting 16kHz mono audio track...")
    audio_path = settings.OUTPUT_DIR / f"{job_id}_en.wav"
    try:
        media_processor.extract_audio(saved_video_path, output_audio_path=audio_path)
    except Exception as e:
        logger.error(f"[{job_id}] Audio extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audio extraction failed: {str(e)}")

    # 3. Transcribe English audio
    active_api_key = api_key_override or settings.GEMINI_API_KEY
    asr_service = ASRService(api_key=active_api_key)
    logger.info(f"[{job_id}] Transcribing English audio...")
    en_segments = await asr_service.transcribe(audio_path)
    en_full_text = " ".join([s.text for s in en_segments])

    # Save English subtitles
    en_sub_paths = save_subtitles([s.model_dump() for s in en_segments], settings.OUTPUT_DIR / f"{job_id}_en")
    en_result = TranslationResult(
        language_code="en",
        language_name="English",
        full_text=en_full_text,
        segments=en_segments,
        srt_file=f"/outputs/{en_sub_paths['srt'].name}",
        vtt_file=f"/outputs/{en_sub_paths['vtt'].name}",
        audio_file=None
    )

    te_result: Optional[TranslationResult] = None
    hi_result: Optional[TranslationResult] = None
    dubbed_video_te: Optional[str] = None
    dubbed_video_hi: Optional[str] = None

    selected_langs = languages.lower().strip()
    process_telugu = selected_langs in ["telugu", "te", "both", "all"]
    process_hindi = selected_langs in ["hindi", "hi", "both", "all"]

    # 4. Module 1: Telugu Translation
    if process_telugu:
        logger.info(f"[{job_id}] Running Module 1: English -> Telugu Translation...")
        te_module = TeluguTranslationModule(api_key=active_api_key)
        te_segments = await te_module.translate_segments(en_segments)
        te_full_text = " ".join([s.text for s in te_segments])
        
        te_sub_paths = save_subtitles([s.model_dump() for s in te_segments], settings.OUTPUT_DIR / f"{job_id}_te")
        
        te_audio_rel = None
        if generate_dubbing:
            te_audio_path = settings.OUTPUT_DIR / f"{job_id}_dubbed_te.mp3"
            logger.info(f"[{job_id}] Synthesizing Telugu neural voiceover...")
            try:
                await tts_service.generate_audio_for_translation(
                    te_segments, language_code="te", output_path=te_audio_path, gender=voice_gender
                )
                te_audio_rel = f"/outputs/{te_audio_path.name}"
                
                # Mux dubbed audio with original video
                dubbed_video_path = settings.OUTPUT_DIR / f"{job_id}_dubbed_te.mp4"
                media_processor.merge_audio_with_video(saved_video_path, te_audio_path, dubbed_video_path)
                dubbed_video_te = f"/outputs/{dubbed_video_path.name}"
            except Exception as e:
                logger.error(f"[{job_id}] Telugu dubbing/merging failed: {e}")

        te_result = TranslationResult(
            language_code="te",
            language_name="Telugu",
            full_text=te_full_text,
            segments=te_segments,
            srt_file=f"/outputs/{te_sub_paths['srt'].name}" if generate_subtitles else None,
            vtt_file=f"/outputs/{te_sub_paths['vtt'].name}" if generate_subtitles else None,
            audio_file=te_audio_rel
        )

    # 5. Module 2: Hindi Translation
    if process_hindi:
        logger.info(f"[{job_id}] Running Module 2: English -> Hindi Translation...")
        hi_module = HindiTranslationModule(api_key=active_api_key)
        hi_segments = await hi_module.translate_segments(en_segments)
        hi_full_text = " ".join([s.text for s in hi_segments])
        
        hi_sub_paths = save_subtitles([s.model_dump() for s in hi_segments], settings.OUTPUT_DIR / f"{job_id}_hi")
        
        hi_audio_rel = None
        if generate_dubbing:
            hi_audio_path = settings.OUTPUT_DIR / f"{job_id}_dubbed_hi.mp3"
            logger.info(f"[{job_id}] Synthesizing Hindi neural voiceover...")
            try:
                await tts_service.generate_audio_for_translation(
                    hi_segments, language_code="hi", output_path=hi_audio_path, gender=voice_gender
                )
                hi_audio_rel = f"/outputs/{hi_audio_path.name}"
                
                # Mux dubbed audio with original video
                dubbed_video_path = settings.OUTPUT_DIR / f"{job_id}_dubbed_hi.mp4"
                media_processor.merge_audio_with_video(saved_video_path, hi_audio_path, dubbed_video_path)
                dubbed_video_hi = f"/outputs/{dubbed_video_path.name}"
            except Exception as e:
                logger.error(f"[{job_id}] Hindi dubbing/merging failed: {e}")

        hi_result = TranslationResult(
            language_code="hi",
            language_name="Hindi",
            full_text=hi_full_text,
            segments=hi_segments,
            srt_file=f"/outputs/{hi_sub_paths['srt'].name}" if generate_subtitles else None,
            vtt_file=f"/outputs/{hi_sub_paths['vtt'].name}" if generate_subtitles else None,
            audio_file=hi_audio_rel
        )

    return VideoTranslationResponse(
        job_id=job_id,
        video_filename=file.filename or "input_video.mp4",
        english_transcript=en_result,
        telugu_translation=te_result,
        hindi_translation=hi_result,
        dubbed_video_telugu=dubbed_video_te,
        dubbed_video_hindi=dubbed_video_hi
    )

@app.post("/api/v1/translate", response_model=VideoTranslationResponse)
async def translate_video(
    file: UploadFile = File(..., description="Video file (MP4, MKV, MOV, WebM, etc.)"),
    languages: str = Form("both", description="Target languages: 'telugu', 'hindi', or 'both'"),
    generate_subtitles: bool = Form(True, description="Generate .srt and .vtt subtitle files"),
    generate_dubbing: bool = Form(True, description="Generate spoken audio voiceover track"),
    voice_gender: str = Form("female", description="Voice gender: 'female' or 'male'"),
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-Api-Key", description="Optional Gemini API key")
):
    """
    Main endpoint: Upload an English video to transcribe and translate into Telugu and/or Hindi.
    """
    return await _process_pipeline(
        file=file,
        languages=languages,
        generate_subtitles=generate_subtitles,
        generate_dubbing=generate_dubbing,
        voice_gender=voice_gender,
        api_key_override=x_gemini_api_key
    )

@app.post("/api/v1/translate/telugu", response_model=VideoTranslationResponse)
async def translate_telugu_only(
    file: UploadFile = File(...),
    generate_subtitles: bool = Form(True),
    generate_dubbing: bool = Form(True),
    voice_gender: str = Form("female"),
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-Api-Key")
):
    """Module 1 Endpoint: Translate English video audio specifically to Telugu."""
    return await _process_pipeline(
        file=file,
        languages="telugu",
        generate_subtitles=generate_subtitles,
        generate_dubbing=generate_dubbing,
        voice_gender=voice_gender,
        api_key_override=x_gemini_api_key
    )

@app.post("/api/v1/translate/hindi", response_model=VideoTranslationResponse)
async def translate_hindi_only(
    file: UploadFile = File(...),
    generate_subtitles: bool = Form(True),
    generate_dubbing: bool = Form(True),
    voice_gender: str = Form("female"),
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-Api-Key")
):
    """Module 2 Endpoint: Translate English video audio specifically to Hindi."""
    return await _process_pipeline(
        file=file,
        languages="hindi",
        generate_subtitles=generate_subtitles,
        generate_dubbing=generate_dubbing,
        voice_gender=voice_gender,
        api_key_override=x_gemini_api_key
    )

@app.get("/api/v1/subtitles/{filename}")
async def get_subtitle_file(filename: str):
    """Download generated subtitle file (.srt or .vtt)."""
    file_path = settings.OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Subtitle file not found")
    media_type = "text/vtt" if filename.endswith(".vtt") else "application/x-subrip"
    return FileResponse(str(file_path), media_type=media_type, filename=filename)

@app.get("/api/v1/audio/{filename}")
async def get_audio_file(filename: str):
    """Stream or download synthesized dubbed audio."""
    file_path = settings.OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(str(file_path), media_type="audio/mpeg", filename=filename)
