import subprocess
import wave
import struct
import math
from pathlib import Path
import pytest
from app.core.media_processor import MediaProcessor

def create_synthetic_wav(path: Path, duration_sec: float = 1.0, sample_rate: int = 16000):
    """Creates a simple 16kHz mono sine-wave WAV file."""
    num_samples = int(duration_sec * sample_rate)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            value = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
            data = struct.pack("<h", value)
            wav_file.writeframes(data)

def test_media_processor_init():
    proc = MediaProcessor()
    assert Path(proc.ffmpeg_exe).exists()

def test_media_audio_extraction(tmp_path):
    proc = MediaProcessor()
    
    # 1. Create a synthetic video container with silent audio using bundled ffmpeg
    dummy_wav = tmp_path / "input.wav"
    create_synthetic_wav(dummy_wav, duration_sec=1.5)
    
    dummy_video = tmp_path / "test_video.mp4"
    # Create an mp4 from the wav
    cmd = [
        proc.ffmpeg_exe,
        "-y",
        "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1.5",
        "-i", str(dummy_wav),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        str(dummy_video)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert res.returncode == 0, f"Failed to generate test video: {res.stderr.decode()}"
    assert dummy_video.exists()

    # 2. Extract audio using MediaProcessor
    extracted_wav = tmp_path / "extracted.wav"
    proc.extract_audio(dummy_video, output_audio_path=extracted_wav)
    
    assert extracted_wav.exists()
    assert extracted_wav.stat().st_size > 0
