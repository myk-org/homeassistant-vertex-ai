"""Base entity for Vertex AI Conversation integration."""

from __future__ import annotations

from typing import Any

from google.genai import Client
from google.genai.types import (
    GenerateContentConfig,
    HarmBlockThreshold,
    HarmCategory,
    SafetySetting,
)

from homeassistant.config_entries import ConfigEntry, ConfigEntrySubEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import (
    DOMAIN,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_HARM_BLOCK_THRESHOLD,
    RECOMMENDED_MAX_TOKENS,
    RECOMMENDED_TEMPERATURE,
    RECOMMENDED_TOP_K,
    RECOMMENDED_TOP_P,
)


class VertexAILLMBaseEntity(Entity):
    """Base entity for Vertex AI LLM entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        config_entry: ConfigEntry,
        subentry: ConfigEntrySubEntry,
    ) -> None:
        """Initialize the entity.

        Args:
            config_entry: The config entry for this integration.
            subentry: The subentry for this specific entity.
        """
        self._config_entry = config_entry
        self._subentry = subentry
        self._attr_unique_id = subentry.subentry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name="Vertex AI",
            manufacturer="Google",
        )

    @property
    def client(self) -> Client:
        """Return the Vertex AI client.

        Returns:
            The authenticated Google GenAI client instance.
        """
        return self.hass.data[DOMAIN][self._config_entry.entry_id]["client"]

    @property
    def options(self) -> dict[str, Any]:
        """Return the subentry options.

        Returns:
            Dictionary containing the subentry configuration data.
        """
        return self._subentry.data

    def get_model_name(self) -> str:
        """Get the configured model name or default.

        Returns:
            The model name to use for content generation.
        """
        return self.options.get("model", RECOMMENDED_CHAT_MODEL)

    def create_generate_content_config(
        self,
        tools: list[Any] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> GenerateContentConfig:
        """Create GenerateContentConfig with safety settings.

        Args:
            tools: Optional list of tools for function calling.
            response_schema: Optional schema for structured output.

        Returns:
            Configured GenerateContentConfig instance with safety settings
            and parameters from options.
        """
        # Get parameters from options with defaults
        temperature = self.options.get("temperature", RECOMMENDED_TEMPERATURE)
        top_p = self.options.get("top_p", RECOMMENDED_TOP_P)
        top_k = self.options.get("top_k", RECOMMENDED_TOP_K)
        max_output_tokens = self.options.get(
            "max_output_tokens", RECOMMENDED_MAX_TOKENS
        )

        # Get harm block threshold
        harm_threshold_str = self.options.get(
            "harm_block_threshold", RECOMMENDED_HARM_BLOCK_THRESHOLD
        )

        # Map string to HarmBlockThreshold enum
        harm_threshold_map = {
            "BLOCK_NONE": HarmBlockThreshold.BLOCK_NONE,
            "BLOCK_ONLY_HIGH": HarmBlockThreshold.BLOCK_ONLY_HIGH,
            "BLOCK_MEDIUM_AND_ABOVE": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            "BLOCK_LOW_AND_ABOVE": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        }
        harm_threshold = harm_threshold_map.get(
            harm_threshold_str, HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
        )

        # Configure safety settings for all harm categories
        safety_settings = [
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=harm_threshold,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=harm_threshold,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=harm_threshold,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=harm_threshold,
            ),
        ]

        # Build config dict
        config_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_output_tokens": max_output_tokens,
            "safety_settings": safety_settings,
        }

        # Add optional parameters if provided
        if tools is not None:
            config_kwargs["tools"] = tools

        if response_schema is not None:
            config_kwargs["response_schema"] = response_schema

        return GenerateContentConfig(**config_kwargs)
