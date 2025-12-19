"""Conversation platform for Vertex AI integration."""

from __future__ import annotations

import logging
from typing import Any

from google.genai.types import Content, Part

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

from .const import SUBENTRY_CONVERSATION
from .entity import VertexAILLMBaseEntity

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
    entities = []

    # Iterate through subentries to find conversation entries
    for subentry in config_entry.subentries:
        if subentry.data.get("subentry_type") == SUBENTRY_CONVERSATION:
            _LOGGER.debug(
                "Creating conversation entity for subentry %s",
                subentry.subentry_id,
            )
            entities.append(VertexAIConversationEntity(config_entry, subentry))

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d Vertex AI conversation entities", len(entities))


class VertexAIConversationEntity(
    ConversationEntity,
    conversation.AbstractConversationAgent,
    VertexAILLMBaseEntity,
):
    """Vertex AI conversation agent entity."""

    _attr_supports_streaming = True
    _attr_name = None

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
        if CONF_LLM_HASS_API in self.options:
            return ConversationEntityFeature.CONTROL
        return ConversationEntityFeature(0)

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
        # Get system prompt from options if configured
        system_prompt = self.options.get("system_prompt")

        # Convert chat log to Vertex AI Content format
        contents = self._convert_chat_log_to_contents(chat_log, user_input)

        # Get model name
        model_name = self.get_model_name()

        _LOGGER.debug(
            "Generating content with model %s (system prompt: %s)",
            model_name,
            "configured" if system_prompt else "not configured",
        )

        # Create generation config
        config = self.create_generate_content_config()

        # Build kwargs for generate_content
        generate_kwargs: dict[str, Any] = {
            "model": model_name,
            "contents": contents,
            "config": config,
        }

        # Add system instruction if provided
        if system_prompt:
            generate_kwargs["system_instruction"] = system_prompt

        try:
            # Call Vertex AI to generate content
            # Run in executor since this is a blocking I/O operation
            response = await self.hass.async_add_executor_job(
                self._generate_content_sync,
                generate_kwargs,
            )

            # Extract response text
            response_text = self._extract_response_text(response)

            _LOGGER.debug("Generated response: %s", response_text[:100])

            # Add response to chat log
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
            _LOGGER.error("Error generating conversation response: %s", err)

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

    def _generate_content_sync(self, kwargs: dict[str, Any]) -> Any:
        """Generate content synchronously (for executor).

        Args:
            kwargs: Keyword arguments for generate_content

        Returns:
            The generated content response
        """
        return self.client.models.generate_content(**kwargs)

    def _convert_chat_log_to_contents(
        self,
        chat_log: list[dict[str, Any]],
        current_input: str,
    ) -> list[Content]:
        """Convert chat log to Vertex AI Content format.

        Args:
            chat_log: List of previous conversation messages
            current_input: The current user input

        Returns:
            List of Content objects for Vertex AI
        """
        contents = []

        # Add previous messages from chat log
        for message in chat_log:
            role = message.get("role", "user")
            content_text = message.get("content", "")

            # Map roles to Vertex AI format
            # Vertex AI uses "user" and "model" roles
            vertex_role = "model" if role == "assistant" else "user"

            contents.append(
                Content(
                    role=vertex_role,
                    parts=[Part(text=content_text)],
                )
            )

        # Add current user input
        contents.append(
            Content(
                role="user",
                parts=[Part(text=current_input)],
            )
        )

        _LOGGER.debug("Converted %d messages to Content format", len(contents))

        return contents

    def _extract_response_text(self, response: Any) -> str:
        """Extract text from Vertex AI response.

        Args:
            response: The Vertex AI generate_content response

        Returns:
            The extracted text content

        Raises:
            ValueError: If response has no text content
        """
        # The response should have a text attribute
        if hasattr(response, "text"):
            return response.text

        # Fallback: try to extract from candidates
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                parts_text = []
                for part in candidate.content.parts:
                    if hasattr(part, "text"):
                        parts_text.append(part.text)
                if parts_text:
                    return "".join(parts_text)

        _LOGGER.error("Could not extract text from response: %s", response)
        raise ValueError("No text content in response")
