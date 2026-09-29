import pytest
from pathlib import Path
from app.utils.subtitle_utils import format_timestamp, generate_srt, generate_vtt, save_subtitles

def test_format_timestamp():
    # 0 seconds
    assert format_timestamp(0.0, is_srt=True) == "00:00:00,000"
    assert format_timestamp(0.0, is_srt=False) == "00:00:00.000"

    # 1 minute, 23 seconds, 456 ms
    t = 60 + 23 + 0.456
    assert format_timestamp(t, is_srt=True) == "00:01:23,456"
    assert format_timestamp(t, is_srt=False) == "00:01:23.456"

    # 1 hour, 15 minutes, 30 seconds
    t2 = 3600 + 15 * 60 + 30
    assert format_timestamp(t2, is_srt=True) == "01:15:30,000"

def test_generate_srt():
    segments = [
        {"id": 1, "start": 1.0, "end": 4.5, "text": "Hello world"},
        {"id": 2, "start": 5.0, "end": 8.2, "text": "Second line"}
    ]
    srt = generate_srt(segments)
    assert "1\n00:00:01,000 --> 00:00:04,500\nHello world" in srt
    assert "2\n00:00:05,000 --> 00:00:08,200\nSecond line" in srt

def test_generate_vtt():
    segments = [
        {"id": 1, "start": 0.5, "end": 2.0, "text": "Intro subtitle"}
    ]
    vtt = generate_vtt(segments)
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.500 --> 00:00:02.000" in vtt
    assert "Intro subtitle" in vtt

def test_save_subtitles(tmp_path):
    segments = [
        {"id": 1, "start": 0.0, "end": 2.0, "text": "Subtitle test"}
    ]
    base_file = tmp_path / "test_sub"
    saved = save_subtitles(segments, base_file)
    
    assert saved["srt"].exists()
    assert saved["vtt"].exists()
    assert saved["srt"].suffix == ".srt"
    assert saved["vtt"].suffix == ".vtt"
