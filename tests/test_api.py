from urllib import response

from fastapi import HTTPException
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app
from tests.test_media import create_synthetic_video

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
    # Create sample video to simulate audio/video upload
    sample_file = tmp_path / "sample.mp4"
    create_synthetic_video(sample_file, duration_sec=1.5)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(sample_file, "rb") as f:
            response = await client.post(
                "/api/v1/translate",
                files={"file": ("sample.mp4", f, "video/mp4")},
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
    sample_file = tmp_path / "sample.mp4"
    create_synthetic_video(sample_file, duration_sec=1.0)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(sample_file, "rb") as f:
            response = await client.post(
                "/api/v1/translate/telugu",
                files={"file": ("sample.mp4", f, "video/mp4")},
                data={"generate_subtitles": "true", "generate_dubbing": "false"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["telugu_translation"] is not None
        assert data["hindi_translation"] is None

@pytest.mark.asyncio
async def test_translate_hindi_only(tmp_path):
    sample_file = tmp_path / "sample.mp4"
    create_synthetic_video(sample_file, duration_sec=1.0)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(sample_file, "rb") as f:
            response = await client.post(
                "/api/v1/translate/hindi",
                files={"file": ("sample.mp4", f, "video/mp4")},
                data={"generate_subtitles": "true", "generate_dubbing": "false"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["telugu_translation"] is None
        assert data["hindi_translation"] is not None

def test_subtitle_path_traversal_blocked():
    from app.main import get_safe_output_file

    with pytest.raises(HTTPException) as exc_info:
        get_safe_output_file(
            r"..\main.py",
            {".srt", ".vtt"},
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid output filename."


def test_audio_path_traversal_blocked():
    from app.main import get_safe_output_file

    with pytest.raises(HTTPException) as exc_info:
        get_safe_output_file(
            r"..\main.py",
            {".mp3", ".wav", ".m4a"},
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid output filename."
@pytest.mark.asyncio
async def test_subtitle_download_success(tmp_path, monkeypatch):
    from app.main import settings

    output_dir = tmp_path / "outputs"
    output_dir.mkdir()

    subtitle_file = output_dir / "sample.srt"
    subtitle_file.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nHello World\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(settings, "OUTPUT_DIR", output_dir)

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/subtitles/sample.srt"
        )

    assert response.status_code == 200
    assert "Hello World" in response.text
def test_output_symlink_escape_blocked(tmp_path, monkeypatch):
    from app.main import get_safe_output_file, settings

    output_dir = tmp_path / "outputs"
    output_dir.mkdir()

    outside_file = tmp_path / "secret.srt"
    outside_file.write_text("Sensitive content", encoding="utf-8")

    symlink = output_dir / "linked.srt"

    try:
        symlink.symlink_to(outside_file)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlink creation is not available: {exc}")

    monkeypatch.setattr(settings, "OUTPUT_DIR", output_dir)

    with pytest.raises(HTTPException) as exc_info:
        get_safe_output_file("linked.srt", {".srt", ".vtt"})

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid output file path."