from pathlib import Path
from typing import List, Dict, Any

def format_timestamp(seconds: float, is_srt: bool = True) -> str:
    """Format seconds into HH:MM:SS,mmm (SRT) or HH:MM:SS.mmm (VTT)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    
    # Clamp millis to 999
    if millis >= 1000:
        millis = 999
        
    separator = "," if is_srt else "."
    return f"{hrs:02d}:{mins:02d}:{secs:02d}{separator}{millis:03d}"

def generate_srt(segments: List[Dict[str, Any]]) -> str:
    """Generate SubRip (.srt) subtitle string from timestamped segments."""
    srt_lines = []
    for idx, seg in enumerate(segments, start=1):
        start_str = format_timestamp(seg.get("start", 0.0), is_srt=True)
        end_str = format_timestamp(seg.get("end", 0.0), is_srt=True)
        text = seg.get("text", "").strip()
        
        srt_lines.append(f"{idx}")
        srt_lines.append(f"{start_str} --> {end_str}")
        srt_lines.append(f"{text}\n")
        
    return "\n".join(srt_lines)

def generate_vtt(segments: List[Dict[str, Any]]) -> str:
    """Generate WebVTT (.vtt) subtitle string from timestamped segments."""
    vtt_lines = ["WEBVTT\n"]
    for idx, seg in enumerate(segments, start=1):
        start_str = format_timestamp(seg.get("start", 0.0), is_srt=False)
        end_str = format_timestamp(seg.get("end", 0.0), is_srt=False)
        text = seg.get("text", "").strip()
        
        vtt_lines.append(f"{idx}")
        vtt_lines.append(f"{start_str} --> {end_str}")
        vtt_lines.append(f"{text}\n")
        
    return "\n".join(vtt_lines)

def save_subtitles(segments: List[Dict[str, Any]], base_path: Path) -> Dict[str, Path]:
    """Save both .srt and .vtt files for the segments."""
    srt_path = base_path.with_suffix(".srt")
    vtt_path = base_path.with_suffix(".vtt")
    
    srt_content = generate_srt(segments)
    vtt_content = generate_vtt(segments)
    
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)
        
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write(vtt_content)
        
    return {
        "srt": srt_path,
        "vtt": vtt_path
    }
