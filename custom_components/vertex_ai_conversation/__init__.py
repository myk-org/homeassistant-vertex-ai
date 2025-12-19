"""The Vertex AI Conversation integration."""

from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import (
    CONF_LOCATION,
    CONF_PROJECT_ID,
    CONF_SERVICE_ACCOUNT_JSON,
    DOMAIN,
    PLATFORMS,
    VERTEX_AI_SCOPES,
)

_LOGGER = logging.getLogger(__name__)

type VertexAIConfigEntry = ConfigEntry[dict[str, Any]]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Vertex AI Conversation component.

    This integration is configured via config flow only.
    YAML configuration is not supported.
    """
    return True


async def async_setup_entry(hass: HomeAssistant, entry: VertexAIConfigEntry) -> bool:
    """Set up Vertex AI Conversation from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry containing credentials and settings

    Returns:
        True if setup was successful

    Raises:
        ConfigEntryAuthFailed: If authentication fails
        ConfigEntryNotReady: If the service is temporarily unavailable
    """
    project_id = entry.data[CONF_PROJECT_ID]
    location = entry.data[CONF_LOCATION]
    service_account_json_str = entry.data[CONF_SERVICE_ACCOUNT_JSON]

    _LOGGER.debug(
        "Setting up Vertex AI Conversation for project %s in location %s",
        project_id,
        location,
    )

    try:
        # Parse service account JSON
        service_account_info = json.loads(service_account_json_str)

        # Create credentials from service account
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=VERTEX_AI_SCOPES,
        )

        _LOGGER.debug("Service account credentials created successfully")

    except json.JSONDecodeError as err:
        _LOGGER.error("Invalid service account JSON: %s", err)
        raise ConfigEntryAuthFailed(
            "Service account JSON is invalid or malformed"
        ) from err
    except (KeyError, ValueError) as err:
        _LOGGER.error("Invalid service account credentials: %s", err)
        raise ConfigEntryAuthFailed(
            "Service account credentials are missing required fields"
        ) from err
    except GoogleAuthError as err:
        _LOGGER.error("Google authentication error: %s", err)
        raise ConfigEntryAuthFailed(
            f"Failed to authenticate with Google: {err}"
        ) from err

    try:
        # Create Vertex AI client
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
            credentials=credentials,
            http_options={"api_version": "v1alpha"},
        )

        _LOGGER.debug("Vertex AI client created successfully")

        # Validate connection by listing models
        # This ensures credentials work and the service is accessible
        def _validate_connection() -> None:
            """Validate connection to Vertex AI (runs in executor)."""
            try:
                # Attempt to list models to verify connectivity
                list(client.models.list())
                _LOGGER.debug("Successfully validated connection to Vertex AI")
            except Exception as err:
                _LOGGER.error("Failed to validate Vertex AI connection: %s", err)
                raise

        # Run validation in executor since it's a blocking operation
        await hass.async_add_executor_job(_validate_connection)

    except GoogleAuthError as err:
        _LOGGER.error("Authentication failed during connection validation: %s", err)
        raise ConfigEntryAuthFailed(
            f"Authentication failed: {err}"
        ) from err
    except Exception as err:
        _LOGGER.error("Failed to connect to Vertex AI: %s", err)
        raise ConfigEntryNotReady(
            f"Unable to connect to Vertex AI service: {err}"
        ) from err

    # Store client and configuration in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "project_id": project_id,
        "location": location,
        "credentials": credentials,
    }

    _LOGGER.info(
        "Vertex AI Conversation setup complete for project %s",
        project_id,
    )

    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: VertexAIConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry to unload

    Returns:
        True if unload was successful
    """
    _LOGGER.debug("Unloading Vertex AI Conversation entry %s", entry.entry_id)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove stored data
        hass.data[DOMAIN].pop(entry.entry_id, None)

        # Clean up domain data if no more entries
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)

        _LOGGER.info("Successfully unloaded Vertex AI Conversation entry")
    else:
        _LOGGER.warning("Failed to unload some platforms")

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: VertexAIConfigEntry) -> bool:
    """Migrate old config entry to new version.

    Args:
        hass: Home Assistant instance
        entry: Config entry to migrate

    Returns:
        True if migration was successful
    """
    _LOGGER.debug(
        "Migrating Vertex AI Conversation entry from version %s.%s",
        entry.version,
        entry.minor_version,
    )

    # Currently at version 1.1, no migrations needed yet
    # Future migrations will be implemented here as the schema evolves

    if entry.version == 1:
        # Placeholder for future version 1 -> 2 migration
        # if entry.minor_version < 2:
        #     # Migration logic here
        #     entry.minor_version = 2
        #     hass.config_entries.async_update_entry(entry)
        pass

    _LOGGER.debug(
        "Migration complete, entry now at version %s.%s",
        entry.version,
        entry.minor_version,
    )

    return True
