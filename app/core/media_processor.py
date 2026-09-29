import subprocess
import json
import logging
from pathlib import Path
from typing import Optional
import imageio_ffmpeg

logger = logging.getLogger(__name__)

class MediaProcessor:
    """Handles audio extraction, probing, and video manipulation using bundled FFmpeg."""
    
    def __init__(self):
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        logger.info(f"Using FFmpeg binary at: {self.ffmpeg_exe}")

    def extract_audio(self, video_path: Path, output_audio_path: Optional[Path] = None, sample_rate: int = 16000) -> Path:
        """
        Extracts mono audio track from a video file at the given sample rate.
        Defaults to 16kHz mono WAV, which is optimal for speech recognition.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        if output_audio_path is None:
            output_audio_path = video_path.with_suffix(".wav")
            
        cmd = [
            self.ffmpeg_exe,
            "-y",                     # Overwrite output without asking
            "-i", str(video_path),    # Input video
            "-vn",                    # Disable video recording
            "-acodec", "pcm_s16le",   # 16-bit uncompressed PCM
            "-ar", str(sample_rate),  # Sample rate (16kHz standard for ASR)
            "-ac", "1",               # Mono channel
            str(output_audio_path)
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg audio extraction failed: {result.stderr}")
            raise RuntimeError(f"FFmpeg extraction error: {result.stderr}")
            
        return output_audio_path

    def merge_audio_with_video(self, video_path: Path, audio_path: Path, output_path: Path) -> Path:
        """
        Replaces the audio track in the video with the provided audio (e.g. translated dub).
        """
        cmd = [
            self.ffmpeg_exe,
            "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",          # Stream copy video (fast, lossless)
            "-c:a", "aac",           # Re-encode audio to AAC
            "-map", "0:v:0",         # Video from first input
            "-map", "1:a:0",         # Audio from second input
            "-shortest",             # Match shortest stream
            str(output_path)
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg audio-video merge failed: {result.stderr}")
            raise RuntimeError(f"FFmpeg merge error: {result.stderr}")
            
        return output_path
