# Video Audio Transcription & Translation (English to Telugu & Hindi)

A high-performance, modular **FastAPI** service that ingests English video files, extracts the audio, transcribes speech with timestamps, and translates into **Telugu (Module 1)** and **Hindi (Module 2)**. It generates standard subtitle files (`.srt` and `.vtt`) and supports natural neural voiceover dubbing using Microsoft Edge-TTS.

---

## 🌟 Key Features

- **Media Processing**: Automatically extracts 16kHz mono audio from uploaded video files (MP4, MKV, MOV, WebM, etc.) using bundled FFmpeg (no manual system-level installation required).
- **Speech-to-Text (ASR)**: Transcribes spoken English with accurate sentence-level timestamp segments.Powered with fallback demo mode.
- **Module 1 (Telugu Engine)**: Context-aware translation of English speech into natural Telugu script (`తెలుగు`) with timestamp synchronization.
- **Module 2 (Hindi Engine)**: Context-aware translation of English speech into natural Hindi (`हिन्दी`) in Devanagari script with timestamp synchronization.
- **Subtitle Generation**: Exports `.srt` (SubRip) and `.vtt` (WebVTT) subtitle tracks for English, Telugu, and Hindi.
- **Neural Voiceover Dubbing**: Generates natural Indic speech using Edge-TTS:
  - Telugu: `te-IN-ShrutiNeural` (Female), `te-IN-MohanNeural` (Male)
  - Hindi: `hi-IN-SwaraNeural` (Female), `hi-IN-MadhurNeural` (Male)
- **Video Dub Muxing**: Automatically merges translated neural audio into a downloadable dubbed MP4 video.
- **Interactive Web Dashboard**: Modern responsive UI with video player, subtitle switching, audio streaming, and side-by-side transcript review.

---

## 🏗️ Architecture

```
                         Uploaded Video
                              │
                              ▼
                    ┌───────────────────┐
                    │  Media Processor  │
                    │      FFmpeg       │
                    └─────────┬─────────┘
                              │
                       Extract Audio
                              │
                              ▼
                    ┌───────────────────┐
                    │       ASR         │
                    │  Speech → Text    │
                    └─────────┬─────────┘
                              │
                     English Segments
                     + Timestamps
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
        ┌─────────────────┐       ┌─────────────────┐
        │ Telugu Module   │       │  Hindi Module   │
        │  English → TE   │       │  English → HI   │
        └────────┬────────┘       └────────┬────────┘
                 │                         │
          ┌──────┴──────┐           ┌──────┴──────┐
          ▼             ▼           ▼             ▼
       SRT/VTT         TTS        SRT/VTT         TTS
          │             │           │             │
          │             └─────┬─────┘             │
          │                   ▼                   │
          │             ┌───────────┐             │
          └────────────►│  FFmpeg   │◄────────────┘
                        │   Muxing  │
                        └─────┬─────┘
                              │
                              ▼
                         Dubbed MP4
```

---

## 📁 Project Structure

```
video-translation-fastapi/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application, CORS, routers & endpoints
│   ├── config.py                   # Pydantic v2 Settings & environment variables
│   ├── core/
│   │   ├── __init__.py
│   │   └── media_processor.py      # Audio extraction & video muxing via imageio-ffmpeg
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract base class & Pydantic response models
│   │   ├── asr_service.py          # English speech-to-text service
│   │   ├── telugu_module.py        # Module 1: English -> Telugu translation
│   │   ├── hindi_module.py         # Module 2: English -> Hindi translation
│   │   └── tts_service.py          # Neural voiceover dubbing (Edge-TTS)
│   ├── utils/
│   │   ├── __init__.py
│   │   └── subtitle_utils.py       # SRT and VTT generator & timestamp formatter
│   └── static/
│       └── index.html              # Modern Web UI dashboard
├── storage/
│   ├── uploads/                    # Temporary uploaded videos
│   └── outputs/                    # Subtitle files, audio tracks, dubbed videos
├── tests/
│   ├── test_api.py                 # FastAPI route integration tests
│   ├── test_media.py               # MediaProcessor & FFmpeg extraction tests
│   ├── test_modules.py             # Telugu & Hindi module tests
│   └── test_subtitles.py           # SRT/VTT formatting tests
├── .env.example                    # Sample environment variables
├── pytest.ini                      # Pytest asyncio configuration
├── requirements.txt                # Python dependencies
└── README.md
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ installed.

### 2. Activate Virtual Environment & Install Dependencies
```powershell
# Navigate to project directory
cd video-translation-fastapi

# Create a virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables (Optional)
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Add your `GEMINI_API_KEY` for live multimodal ASR and translation:
```env
GEMINI_API_KEY="your_api_key_here"
```
*(Note: If left blank, the system automatically runs in fallback demo mode, allowing end-to-end testing without an API key!)*

### 4. Run the Server
```powershell
.\venv\Scripts\uvicorn app.main:app --reload --port 8000
```

- **Web Dashboard**: Open [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: Open [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📡 API Endpoints

### 1. `POST /api/v1/translate` (Main Pipeline)
Upload a video file and translate into Telugu, Hindi, or both.

**Form Parameters:**
- `file` *(UploadFile)*: Video or audio file (MP4, MKV, MOV, WebM, WAV, MP3).
- `languages` *(str, default "both")*: `"telugu"`, `"hindi"`, or `"both"`.
- `generate_subtitles` *(bool, default true)*: Creates `.srt` and `.vtt` files.
- `generate_dubbing` *(bool, default true)*: Synthesizes regional voiceover audio.
- `voice_gender` *(str, default "female")*: `"female"` or `"male"`.
- Header `X-Gemini-Api-Key` *(optional)*: Gemini API key for this request.

**Sample JSON Response:**
```json
{
  "job_id": "8f3a91c2",
  "video_filename": "lecture.mp4",
  "english_transcript": {
    "language_code": "en",
    "language_name": "English",
    "full_text": "Welcome to this demonstration of automated video translation...",
    "segments": [
      {
        "id": 1,
        "start": 0.0,
        "end": 3.5,
        "text": "Welcome to this demonstration of automated video translation."
      }
    ],
    "srt_file": "/outputs/8f3a91c2_en.srt",
    "vtt_file": "/outputs/8f3a91c2_en.vtt"
  },
  "telugu_translation": {
    "language_code": "te",
    "language_name": "Telugu",
    "full_text": "ఆటోమేటెడ్ వీడియో అనువాదం యొక్క ఈ ప్రదర్శనకు స్వాగతం...",
    "segments": [
      {
        "id": 1,
        "start": 0.0,
        "end": 3.5,
        "text": "ఆటోమేటెడ్ వీడియో అనువాదం యొక్క ఈ ప్రదర్శనకు స్వాగతం."
      }
    ],
    "srt_file": "/outputs/8f3a91c2_te.srt",
    "vtt_file": "/outputs/8f3a91c2_te.vtt",
    "audio_file": "/outputs/8f3a91c2_dubbed_te.mp3"
  },
  "hindi_translation": {
    "language_code": "hi",
    "language_name": "Hindi",
    "full_text": "स्वचालित वीडियो अनुवाद के इस प्रदर्शन में आपका स्वागत है...",
    "segments": [
      {
        "id": 1,
        "start": 0.0,
        "end": 3.5,
        "text": "स्वचालित वीडियो अनुवाद के इस प्रदर्शन में आपका स्वागत है।"
      }
    ],
    "srt_file": "/outputs/8f3a91c2_hi.srt",
    "vtt_file": "/outputs/8f3a91c2_hi.vtt",
    "audio_file": "/outputs/8f3a91c2_dubbed_hi.mp3"
  },
  "dubbed_video_telugu": "/outputs/8f3a91c2_dubbed_te.mp4",
  "dubbed_video_hindi": "/outputs/8f3a91c2_dubbed_hi.mp4"
}
```

### 2. `POST /api/v1/translate/telugu`
Dedicated convenience endpoint specifically for Module 1 (English to Telugu).

### 3. `POST /api/v1/translate/hindi`
Dedicated convenience endpoint specifically for Module 2 (English to Hindi).

### 4. `GET /api/v1/health`
Health check reporting system status, active modules, and FFmpeg readiness.

---

## 🧪 Running Automated Tests

Run the complete test suite:
```powershell
.\venv\Scripts\python -m pytest -v tests/
```
The test suite covers audio extraction, timestamp conversion,
subtitle generation, Telugu and Hindi translation modules,
TTS voice mapping, and FastAPI integration routes.

---

## Limitations

- Translation and transcription quality depend on the configured AI model.
- Processing time depends on video duration and available system resources.
- Generated media files are stored locally.
- Current dubbing generates a continuous translated audio track; precise
  segment-level audio synchronization can be improved in a future version.
- Large video files may require additional processing time and memory.