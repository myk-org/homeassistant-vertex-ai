"""Helper utilities for Vertex AI Conversation integration."""

from __future__ import annotations

import io
import logging
import re
import wave

_LOGGER = logging.getLogger(__name__)

# Default audio parameters
DEFAULT_SAMPLE_RATE = 24000
DEFAULT_BITS_PER_SAMPLE = 16


def _parse_audio_mime_type(mime_type: str) -> tuple[int, int]:
    """Parse audio MIME type to extract sample rate and bits per sample.

    Args:
        mime_type: MIME type string (e.g., "audio/L16;rate=16000")

    Returns:
        Tuple of (sample_rate, bits_per_sample)

    Examples:
        >>> _parse_audio_mime_type("audio/L16")
        (24000, 16)
        >>> _parse_audio_mime_type("audio/L16;rate=16000")
        (16000, 16)
        >>> _parse_audio_mime_type("audio/pcm")
        (24000, 16)
    """
    sample_rate = DEFAULT_SAMPLE_RATE
    bits_per_sample = DEFAULT_BITS_PER_SAMPLE

    # Extract bits per sample from format (e.g., L16 -> 16 bits)
    bits_match = re.search(r"L(\d+)", mime_type)
    if bits_match:
        bits_per_sample = int(bits_match.group(1))

    # Extract sample rate from parameters (e.g., rate=16000)
    rate_match = re.search(r"rate=(\d+)", mime_type)
    if rate_match:
        sample_rate = int(rate_match.group(1))

    _LOGGER.debug(
        "Parsed MIME type '%s': sample_rate=%d, bits_per_sample=%d",
        mime_type,
        sample_rate,
        bits_per_sample,
    )

    return sample_rate, bits_per_sample


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Convert audio data to WAV format.

    Args:
        audio_data: Raw audio bytes
        mime_type: MIME type of the audio (e.g., "audio/L16;rate=24000")

    Returns:
        WAV formatted audio bytes

    Raises:
        ValueError: If audio data is empty or invalid
        OSError: If WAV writing fails
    """
    if not audio_data:
        raise ValueError("Audio data cannot be empty")

    try:
        sample_rate, bits_per_sample = _parse_audio_mime_type(mime_type)

        # Calculate audio parameters
        sample_width = bits_per_sample // 8  # Convert bits to bytes
        num_channels = 1  # Mono audio

        # Create WAV file in memory
        wav_buffer = io.BytesIO()

        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(num_channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)

        wav_bytes = wav_buffer.getvalue()

        _LOGGER.debug(
            "Converted %d bytes of audio to WAV format (%d Hz, %d-bit, %d channel(s))",
            len(audio_data),
            sample_rate,
            bits_per_sample,
            num_channels,
        )

        return wav_bytes

    except ValueError as err:
        _LOGGER.error("Invalid audio parameters: %s", err)
        raise
    except OSError as err:
        _LOGGER.error("Failed to write WAV file: %s", err)
        raise
    except Exception as err:
        _LOGGER.error("Unexpected error converting audio to WAV: %s", err)
        raise ValueError(f"Failed to convert audio to WAV: {err}") from err
