"""AI Task entity for Vertex AI Conversation integration."""

from __future__ import annotations

import logging
from typing import Any

from google.genai.types import Content, Part

from homeassistant.components.ai_task import (
    AITaskEntity,
    AITaskEntityFeature,
    GenDataTask,
    GenDataTaskResult,
)
from homeassistant.config_entries import ConfigEntry, ConfigEntrySubEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SUBENTRY_AI_TASK
from .entity import VertexAILLMBaseEntity

_LOGGER = logging.getLogger(__name__)


class VertexAITaskEntity(AITaskEntity, VertexAILLMBaseEntity):
    """Vertex AI implementation of AI Task entity."""

    _attr_name = None
    _attr_supported_features = AITaskEntityFeature.GENERATE_DATA

    def __init__(
        self,
        config_entry: ConfigEntry,
        subentry: ConfigEntrySubEntry,
    ) -> None:
        """Initialize the AI task entity.

        Args:
            config_entry: The config entry for this integration.
            subentry: The subentry for this specific AI task entity.
        """
        VertexAILLMBaseEntity.__init__(self, config_entry, subentry)

    async def _async_generate_data(self, task: GenDataTask) -> GenDataTaskResult:
        """Generate data based on the task instructions.

        Args:
            task: The task containing instructions and optional structure schema.

        Returns:
            GenDataTaskResult with the generated data.

        Raises:
            Exception: If content generation fails.
        """
        _LOGGER.debug("Generating data for task: %s", task.instructions)

        # Get model name from options
        model_name = self.get_model_name()
        _LOGGER.debug("Using model: %s", model_name)

        # Build content from task instructions
        content = Content(
            parts=[Part(text=task.instructions)],
        )

        # Create generation config with optional response_schema
        response_schema = None
        if task.structure:
            _LOGGER.debug("Task has structure schema: %s", task.structure)
            response_schema = task.structure

        generate_config = self.create_generate_content_config(
            response_schema=response_schema
        )

        _LOGGER.debug("Generation config created")

        # Call client to generate content
        try:
            _LOGGER.debug("Calling Vertex AI to generate content")

            def _generate_content() -> Any:
                """Generate content synchronously (runs in executor).

                Returns:
                    The generated response from Vertex AI.
                """
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=content,
                    config=generate_config,
                )
                return response

            # Run in executor since it's a blocking operation
            response = await self.hass.async_add_executor_job(_generate_content)

            _LOGGER.debug("Content generation completed successfully")

            # Extract data from response
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    # Get the text from the first part
                    response_text = candidate.content.parts[0].text
                    _LOGGER.debug("Generated text: %s", response_text)

                    # If structured output was requested, the response should be JSON
                    if response_schema:
                        import json

                        try:
                            response_data = json.loads(response_text)
                            _LOGGER.debug(
                                "Parsed structured response: %s", response_data
                            )
                            return GenDataTaskResult(data=response_data)
                        except json.JSONDecodeError as err:
                            _LOGGER.error(
                                "Failed to parse structured response as JSON: %s", err
                            )
                            # Return as text if JSON parsing fails
                            return GenDataTaskResult(data={"text": response_text})
                    else:
                        # Return as text for unstructured output
                        return GenDataTaskResult(data={"text": response_text})

            # No valid response received
            _LOGGER.warning("No valid response from Vertex AI")
            return GenDataTaskResult(data={"error": "No valid response generated"})

        except Exception as err:
            _LOGGER.error("Error generating content: %s", err)
            raise


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vertex AI Task entities from a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry for this integration.
        async_add_entities: Callback to add entities.
    """
    _LOGGER.debug("Setting up AI Task entities for entry: %s", entry.entry_id)

    # Get all subentries for this config entry
    subentries = hass.config_entries.async_get_subentries(entry.entry_id)

    # Filter for AI task subentries
    ai_task_subentries = [
        subentry
        for subentry in subentries
        if subentry.data.get("subentry_type") == SUBENTRY_AI_TASK
    ]

    _LOGGER.debug("Found %d AI task subentries", len(ai_task_subentries))

    # Create entities for each AI task subentry
    entities = [VertexAITaskEntity(entry, subentry) for subentry in ai_task_subentries]

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d AI task entities", len(entities))
    else:
        _LOGGER.debug("No AI task entities to add")
