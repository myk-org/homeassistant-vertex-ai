"""Text-to-speech support for Vertex AI Conversation integration."""

from __future__ import annotations

import base64
import logging
from typing import Any

from google.genai.types import (
    GenerateContentConfig,
    Modality,
    SpeechConfig,
    VoiceConfig,
)

from homeassistant.components.tts import TextToSpeechEntity, TtsAudioType, Voice
from homeassistant.config_entries import ConfigEntry, ConfigEntrySubEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import RECOMMENDED_TTS_MODEL, SUBENTRY_TTS
from .entity import VertexAILLMBaseEntity

_LOGGER = logging.getLogger(__name__)

# Available Gemini TTS voices
GEMINI_VOICES = [
    "Puck",
    "Charon",
    "Kore",
    "Fenrir",
    "Aoede",
]

# Supported languages for Gemini TTS
SUPPORTED_LANGUAGES = [
    "en",  # English
    "es",  # Spanish
    "fr",  # French
    "de",  # German
    "it",  # Italian
    "pt",  # Portuguese
    "nl",  # Dutch
    "pl",  # Polish
    "ru",  # Russian
    "ja",  # Japanese
    "ko",  # Korean
    "zh",  # Chinese
    "ar",  # Arabic
    "hi",  # Hindi
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vertex AI TTS from a config entry.

    Args:
        hass: Home Assistant instance
        config_entry: The config entry for this integration
        async_add_entities: Callback to add entities
    """
    # Get subentries for TTS
    tts_subentries = [
        subentry
        for subentry in config_entry.subentries
        if subentry.data.get("subentry_type") == SUBENTRY_TTS
    ]

    if not tts_subentries:
        _LOGGER.debug("No TTS subentries found for config entry %s", config_entry.entry_id)
        return

    entities = [
        VertexAITTSEntity(config_entry, subentry)
        for subentry in tts_subentries
    ]

    _LOGGER.debug("Setting up %d Vertex AI TTS entities", len(entities))
    async_add_entities(entities)


class VertexAITTSEntity(TextToSpeechEntity, VertexAILLMBaseEntity):
    """Vertex AI Text-to-Speech entity."""

    _attr_name = None

    def __init__(
        self,
        config_entry: ConfigEntry,
        subentry: ConfigEntrySubEntry,
    ) -> None:
        """Initialize the TTS entity.

        Args:
            config_entry: The config entry for this integration.
            subentry: The subentry for this TTS entity.
        """
        VertexAILLMBaseEntity.__init__(self, config_entry, subentry)
        _LOGGER.debug("Initialized Vertex AI TTS entity with ID %s", self._attr_unique_id)

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages.

        Returns:
            List of language codes supported by Gemini TTS.
        """
        return SUPPORTED_LANGUAGES

    @property
    def default_language(self) -> str:
        """Return the default language.

        Returns:
            Default language code (English).
        """
        return "en"

    async def async_get_supported_voices(self, language: str) -> list[Voice]:
        """Return a list of supported voices for a language.

        Args:
            language: Language code to get voices for.

        Returns:
            List of Voice objects with available Gemini voices.
        """
        if language not in SUPPORTED_LANGUAGES:
            _LOGGER.warning("Language %s not supported, returning empty voice list", language)
            return []

        voices = [
            Voice(voice_id=voice, name=voice)
            for voice in GEMINI_VOICES
        ]

        _LOGGER.debug("Returning %d voices for language %s", len(voices), language)
        return voices

    async def async_get_tts_audio(
        self,
        message: str,
        language: str,
        options: dict[str, Any] | None = None,
    ) -> TtsAudioType:
        """Generate TTS audio from text.

        Args:
            message: Text message to convert to speech.
            language: Language code for the speech.
            options: Optional parameters including model and voice settings.

        Returns:
            Tuple of (audio_format, audio_data) where audio_format is the file
            extension and audio_data is the raw audio bytes.

        Raises:
            Exception: If audio generation fails.
        """
        options = options or {}

        # Get model from options or use default
        model = options.get("model", RECOMMENDED_TTS_MODEL)

        # Get voice from options or use default
        voice = options.get("voice", "Puck")

        _LOGGER.debug(
            "Generating TTS audio for language=%s, model=%s, voice=%s, message_length=%d",
            language,
            model,
            voice,
            len(message),
        )

        try:
            # Create voice configuration
            voice_config = VoiceConfig(name=voice)

            # Create speech configuration
            speech_config = SpeechConfig(voice_config=voice_config)

            # Create generation config with audio modality
            generate_config = GenerateContentConfig(
                response_modalities=[Modality.AUDIO],
                speech_config=speech_config,
            )

            # Generate content with audio
            def _generate_audio() -> bytes:
                """Generate audio in executor (blocking operation)."""
                response = self.client.models.generate_content(
                    model=model,
                    contents=message,
                    config=generate_config,
                )

                # Extract audio data from response
                # The audio data is in the response parts
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        # Audio data is base64 encoded
                        audio_bytes = base64.b64decode(part.inline_data.data)
                        _LOGGER.debug("Successfully generated %d bytes of audio", len(audio_bytes))
                        return audio_bytes

                raise ValueError("No audio data found in response")

            # Run generation in executor since it's a blocking operation
            audio_data = await self.hass.async_add_executor_job(_generate_audio)

            # Return WAV format and audio data
            return ("wav", audio_data)

        except Exception as err:
            _LOGGER.error(
                "Failed to generate TTS audio: %s (model=%s, voice=%s, language=%s)",
                err,
                model,
                voice,
                language,
            )
            raise
