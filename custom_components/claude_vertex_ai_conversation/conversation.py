"""Conversation platform for Vertex AI integration."""

from __future__ import annotations

import logging
from typing import Any

from anthropic import AnthropicVertex

from homeassistant.components import conversation
from homeassistant.components.conversation import (
    ConversationEntity,
    ConversationEntityFeature,
    ConversationResult,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LLM_HASS_API, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, RECOMMENDED_CHAT_MODEL, RECOMMENDED_MAX_TOKENS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vertex AI conversation entities from a config entry.

    Args:
        hass: Home Assistant instance
        config_entry: The config entry for this integration
        async_add_entities: Callback to add entities
    """
    # Create a single conversation entity for this config entry
    _LOGGER.debug("Creating conversation entity for entry %s", config_entry.entry_id)
    async_add_entities([VertexAIConversationEntity(hass, config_entry)])
    _LOGGER.info("Added Vertex AI conversation entity")


class VertexAIConversationEntity(
    ConversationEntity,
    conversation.AbstractConversationAgent,
):
    """Vertex AI Claude conversation agent entity."""

    _attr_supports_streaming = False
    _attr_name = None
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the conversation entity.

        Args:
            hass: Home Assistant instance
            config_entry: The config entry for this integration
        """
        self.hass = hass
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_conversation"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Claude (Vertex AI)",
            "manufacturer": "Anthropic",
            "model": "Claude via Vertex AI",
        }

    @property
    def supported_languages(self) -> list[str] | str:
        """Return list of supported languages.

        Returns:
            MATCH_ALL to indicate all languages are supported.
        """
        return MATCH_ALL

    @property
    def supported_features(self) -> ConversationEntityFeature:
        """Return supported features.

        Returns:
            ConversationEntityFeature.CONTROL if LLM HASS API is configured,
            otherwise 0 (no additional features).
        """
        options = self._config_entry.options
        if CONF_LLM_HASS_API in options:
            return ConversationEntityFeature.CONTROL
        return ConversationEntityFeature(0)

    @property
    def client(self) -> AnthropicVertex:
        """Return the Anthropic Vertex AI client.

        Returns:
            The authenticated AnthropicVertex client instance.
        """
        return self.hass.data[DOMAIN][self._config_entry.entry_id]["client"]

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, register as conversation agent."""
        await super().async_added_to_hass()

        # Register this entity as a conversation agent
        conversation.async_set_agent(
            self.hass,
            self._config_entry,
            self,
        )

        _LOGGER.debug(
            "Registered Vertex AI conversation agent: %s",
            self.entity_id,
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity is removed, unregister from conversation agent."""
        # Unregister from conversation
        conversation.async_unset_agent(
            self.hass,
            self._config_entry,
            self,
        )

        _LOGGER.debug(
            "Unregistered Vertex AI conversation agent: %s",
            self.entity_id,
        )

        await super().async_will_remove_from_hass()

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a user input message.

        Args:
            user_input: The user's conversation input

        Returns:
            ConversationResult with the agent's response
        """
        # Extract the text and conversation history from the input
        user_message = user_input.text
        chat_log = user_input.conversation_id or []

        _LOGGER.debug(
            "Processing conversation message: %s (history length: %d)",
            user_message,
            len(chat_log),
        )

        # Handle the message using the internal handler
        result = await self._async_handle_message(user_input, user_message, chat_log)

        return result

    async def _async_handle_message(
        self,
        conversation_input: conversation.ConversationInput,
        user_input: str,
        chat_log: list[dict[str, Any]],
    ) -> ConversationResult:
        """Handle a conversation message.

        Args:
            conversation_input: The original ConversationInput object
            user_input: The user's message text
            chat_log: The conversation history

        Returns:
            ConversationResult with the agent's response
        """
        # Get configuration from options
        options = self._config_entry.options
        system_prompt = options.get("system_prompt")
        model_name = options.get("model", RECOMMENDED_CHAT_MODEL)
        max_tokens = options.get("max_tokens", RECOMMENDED_MAX_TOKENS)
        temperature = options.get("temperature", 1.0)

        _LOGGER.debug(
            "Generating content with model %s (system prompt: %s)",
            model_name,
            "configured" if system_prompt else "not configured",
        )

        # Convert chat log to Anthropic messages format
        messages = self._convert_chat_log_to_messages(chat_log, user_input)

        # Build kwargs for messages.create
        create_kwargs: dict[str, Any] = {
            "model": model_name,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
        }

        # Add system prompt if provided
        if system_prompt:
            create_kwargs["system"] = system_prompt

        try:
            # Call Anthropic Vertex AI to generate content
            # Run in executor since this is a blocking I/O operation
            response = await self.hass.async_add_executor_job(
                lambda: self.client.messages.create(**create_kwargs)
            )

            # Extract response text from the first content block
            response_text = response.content[0].text

            _LOGGER.debug("Generated response: %s", response_text[:100])

            # Add messages to chat log
            chat_log.append({"role": "user", "content": user_input})
            chat_log.append({"role": "assistant", "content": response_text})

            # Create and return ConversationResult
            return ConversationResult(
                response=conversation.ConversationResponse(
                    speech={
                        "plain": {
                            "speech": response_text,
                            "extra_data": None,
                        }
                    },
                    language=conversation_input.language if hasattr(conversation_input, "language") else None,
                ),
                conversation_id=chat_log,
            )

        except Exception as err:
            _LOGGER.error("Error generating conversation response: %s", err, exc_info=True)

            # Return error response
            error_message = (
                "Sorry, I encountered an error while processing your request. "
                "Please try again."
            )

            return ConversationResult(
                response=conversation.ConversationResponse(
                    speech={
                        "plain": {
                            "speech": error_message,
                            "extra_data": None,
                        }
                    },
                    language=conversation_input.language if hasattr(conversation_input, "language") else None,
                ),
                conversation_id=chat_log,
            )

    def _convert_chat_log_to_messages(
        self,
        chat_log: list[dict[str, Any]],
        current_input: str,
    ) -> list[dict[str, str]]:
        """Convert chat log to Anthropic messages format.

        Args:
            chat_log: List of previous conversation messages
            current_input: The current user input

        Returns:
            List of message dicts for Anthropic API
        """
        messages = []

        # Add previous messages from chat log
        for message in chat_log:
            role = message.get("role", "user")
            content_text = message.get("content", "")

            # Anthropic uses "user" and "assistant" roles
            messages.append({
                "role": role,
                "content": content_text,
            })

        # Add current user input
        messages.append({
            "role": "user",
            "content": current_input,
        })

        _LOGGER.debug("Converted %d messages to Anthropic format", len(messages))

        return messages
