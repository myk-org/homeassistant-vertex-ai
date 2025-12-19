"""Speech-to-text platform for Vertex AI Conversation integration."""

from __future__ import annotations

import logging
from typing import Any

from google.genai.types import Part

from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
    SpeechToTextEntity,
)
from homeassistant.config_entries import ConfigEntry, ConfigEntrySubEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SUBENTRY_STT
from .entity import VertexAILLMBaseEntity

_LOGGER = logging.getLogger(__name__)


class VertexAISTTEntity(SpeechToTextEntity, VertexAILLMBaseEntity):
    """Vertex AI Speech-to-Text entity."""

    _attr_name = None

    def __init__(
        self,
        config_entry: ConfigEntry,
        subentry: ConfigEntrySubEntry,
    ) -> None:
        """Initialize the STT entity.

        Args:
            config_entry: The config entry for this integration.
            subentry: The subentry for this specific STT entity.
        """
        VertexAILLMBaseEntity.__init__(self, config_entry, subentry)

    @property
    def supported_languages(self) -> list[str]:
        """Return the list of supported locale codes.

        Returns:
            List of locale codes supported by Vertex AI STT.
        """
        return [
            "en-US",  # English (United States)
            "en-GB",  # English (United Kingdom)
            "en-AU",  # English (Australia)
            "en-CA",  # English (Canada)
            "en-IN",  # English (India)
            "es-ES",  # Spanish (Spain)
            "es-MX",  # Spanish (Mexico)
            "es-US",  # Spanish (United States)
            "fr-FR",  # French (France)
            "fr-CA",  # French (Canada)
            "de-DE",  # German (Germany)
            "it-IT",  # Italian (Italy)
            "pt-BR",  # Portuguese (Brazil)
            "pt-PT",  # Portuguese (Portugal)
            "ja-JP",  # Japanese (Japan)
            "ko-KR",  # Korean (South Korea)
            "zh-CN",  # Chinese (Simplified, China)
            "zh-TW",  # Chinese (Traditional, Taiwan)
            "nl-NL",  # Dutch (Netherlands)
            "pl-PL",  # Polish (Poland)
            "ru-RU",  # Russian (Russia)
            "ar-SA",  # Arabic (Saudi Arabia)
            "hi-IN",  # Hindi (India)
            "sv-SE",  # Swedish (Sweden)
            "da-DK",  # Danish (Denmark)
            "fi-FI",  # Finnish (Finland)
            "no-NO",  # Norwegian (Norway)
            "tr-TR",  # Turkish (Turkey)
            "cs-CZ",  # Czech (Czech Republic)
            "th-TH",  # Thai (Thailand)
            "vi-VN",  # Vietnamese (Vietnam)
        ]

    @property
    def supported_formats(self) -> list[AudioFormats]:
        """Return the list of supported audio formats.

        Returns:
            List of supported audio formats.
        """
        return [AudioFormats.WAV, AudioFormats.OGG, AudioFormats.FLAC]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        """Return the list of supported audio codecs.

        Returns:
            List of supported audio codecs.
        """
        return [AudioCodecs.PCM, AudioCodecs.OPUS, AudioCodecs.FLAC]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        """Return the list of supported audio bit rates.

        Returns:
            List of supported audio bit rates.
        """
        return [
            AudioBitRates.BITRATE_8,
            AudioBitRates.BITRATE_16,
            AudioBitRates.BITRATE_24,
            AudioBitRates.BITRATE_32,
        ]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        """Return the list of supported audio sample rates.

        Returns:
            List of supported audio sample rates.
        """
        return [
            AudioSampleRates.SAMPLERATE_8000,
            AudioSampleRates.SAMPLERATE_16000,
            AudioSampleRates.SAMPLERATE_22050,
            AudioSampleRates.SAMPLERATE_44100,
            AudioSampleRates.SAMPLERATE_48000,
        ]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        """Return the list of supported audio channels.

        Returns:
            List of supported audio channels.
        """
        return [AudioChannels.CHANNEL_MONO, AudioChannels.CHANNEL_STEREO]

    async def async_process_audio_stream(
        self,
        metadata: SpeechMetadata,
        stream: Any,
    ) -> SpeechResult:
        """Process an audio stream to text.

        Args:
            metadata: Metadata about the audio stream.
            stream: Async generator yielding audio chunks.

        Returns:
            SpeechResult containing the transcribed text or error state.
        """
        _LOGGER.debug(
            "Processing audio stream with format=%s, codec=%s, language=%s",
            metadata.format,
            metadata.codec,
            metadata.language,
        )

        try:
            # Collect all audio chunks from the stream
            audio_data = bytearray()
            async for chunk in stream:
                audio_data.extend(chunk)

            if not audio_data:
                _LOGGER.warning("Received empty audio stream")
                return SpeechResult(
                    text="",
                    result=SpeechResultState.ERROR,
                )

            _LOGGER.debug("Collected %d bytes of audio data", len(audio_data))

            # Determine MIME type based on format and codec
            mime_type = self._get_mime_type(metadata.format, metadata.codec)
            _LOGGER.debug("Using MIME type: %s", mime_type)

            # Create audio part with inline data
            audio_part = Part(
                inline_data={
                    "mime_type": mime_type,
                    "data": bytes(audio_data),
                }
            )

            # Create prompt for transcription
            prompt = "Transcribe this audio."
            if metadata.language:
                # Add language hint to improve accuracy
                prompt = f"Transcribe this audio in {metadata.language}."

            # Get model name from options
            model_name = self.get_model_name()
            _LOGGER.debug("Using model: %s", model_name)

            # Generate content with audio and prompt
            def _generate_transcription() -> str:
                """Generate transcription (runs in executor)."""
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[audio_part, prompt],
                )
                return response.text

            # Run in executor since it's a blocking operation
            transcribed_text = await self.hass.async_add_executor_job(
                _generate_transcription
            )

            _LOGGER.debug("Transcription successful: %s", transcribed_text)

            return SpeechResult(
                text=transcribed_text,
                result=SpeechResultState.SUCCESS,
            )

        except Exception as err:
            _LOGGER.error("Error processing audio stream: %s", err, exc_info=True)
            return SpeechResult(
                text="",
                result=SpeechResultState.ERROR,
            )

    def _get_mime_type(self, format: str, codec: str) -> str:
        """Get MIME type from format and codec.

        Args:
            format: Audio format (e.g., 'wav', 'ogg', 'flac').
            codec: Audio codec (e.g., 'pcm', 'opus', 'flac').

        Returns:
            Appropriate MIME type string.
        """
        # Map common format/codec combinations to MIME types
        if format == AudioFormats.WAV:
            return "audio/wav"
        elif format == AudioFormats.OGG:
            if codec == AudioCodecs.OPUS:
                return "audio/ogg; codecs=opus"
            return "audio/ogg"
        elif format == AudioFormats.FLAC:
            return "audio/flac"

        # Default fallback
        _LOGGER.warning(
            "Unknown format/codec combination: %s/%s, defaulting to audio/wav",
            format,
            codec,
        )
        return "audio/wav"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vertex AI STT entities from config entry.

    Args:
        hass: Home Assistant instance.
        config_entry: Config entry containing credentials and settings.
        async_add_entities: Callback to add entities to Home Assistant.
    """
    _LOGGER.debug("Setting up Vertex AI STT entities for entry %s", config_entry.entry_id)

    # Get all STT subentries
    stt_subentries = [
        subentry
        for subentry in config_entry.subentries
        if subentry.data.get("subentry_type") == SUBENTRY_STT
    ]

    if not stt_subentries:
        _LOGGER.debug("No STT subentries found")
        return

    # Create STT entities
    entities = [
        VertexAISTTEntity(config_entry, subentry)
        for subentry in stt_subentries
    ]

    _LOGGER.info("Adding %d Vertex AI STT entities", len(entities))
    async_add_entities(entities)
