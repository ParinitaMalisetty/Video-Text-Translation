import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app
from tests.test_media import create_synthetic_wav

@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "module_1" in data["modules"]
        assert "module_2" in data["modules"]

@pytest.mark.asyncio
async def test_root_dashboard():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "Video Audio Translator" in response.text

@pytest.mark.asyncio
async def test_translate_endpoint_pipeline(tmp_path):
    # Create sample WAV to simulate audio/video upload
    sample_file = tmp_path / "sample.wav"
    create_synthetic_wav(sample_file, duration_sec=1.5)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(sample_file, "rb") as f:
            response = await client.post(
                "/api/v1/translate",
                files={"file": ("sample.wav", f, "audio/wav")},
                data={
                    "languages": "both",
                    "generate_subtitles": "true",
                    "generate_dubbing": "false",
                    "voice_gender": "female"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["english_transcript"]["language_code"] == "en"
        assert data["telugu_translation"]["language_code"] == "te"
        assert data["hindi_translation"]["language_code"] == "hi"
        assert len(data["english_transcript"]["segments"]) > 0
        assert len(data["telugu_translation"]["segments"]) > 0
        assert len(data["hindi_translation"]["segments"]) > 0

@pytest.mark.asyncio
async def test_translate_telugu_only(tmp_path):
    sample_file = tmp_path / "sample.wav"
    create_synthetic_wav(sample_file, duration_sec=1.0)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(sample_file, "rb") as f:
            response = await client.post(
                "/api/v1/translate/telugu",
                files={"file": ("sample.wav", f, "audio/wav")},
                data={"generate_subtitles": "true", "generate_dubbing": "false"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["telugu_translation"] is not None
        assert data["hindi_translation"] is None

@pytest.mark.asyncio
async def test_translate_hindi_only(tmp_path):
    sample_file = tmp_path / "sample.wav"
    create_synthetic_wav(sample_file, duration_sec=1.0)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(sample_file, "rb") as f:
            response = await client.post(
                "/api/v1/translate/hindi",
                files={"file": ("sample.wav", f, "audio/wav")},
                data={"generate_subtitles": "true", "generate_dubbing": "false"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["telugu_translation"] is None
        assert data["hindi_translation"] is not None
