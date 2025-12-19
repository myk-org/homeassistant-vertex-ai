"""The Vertex AI Conversation integration."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any

from anthropic import AnthropicVertex
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

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
        # Parse credentials JSON
        credentials_info = json.loads(service_account_json_str)

        # Determine credential type and create appropriate credentials object
        credential_type = credentials_info.get("type")

        if credential_type == "service_account":
            # Create credentials from service account
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=VERTEX_AI_SCOPES,
            )
            _LOGGER.debug("Service account credentials created successfully")

        elif credential_type == "authorized_user":
            # Use the built-in method for authorized_user credentials
            # This properly handles all fields from the ADC authorized_user JSON format
            # IMPORTANT: Remove quota_project_id from the dict to avoid conflicts
            credentials_info_clean = {
                k: v for k, v in credentials_info.items() if k != "quota_project_id"
            }
            credentials = Credentials.from_authorized_user_info(
                credentials_info_clean,
                scopes=VERTEX_AI_SCOPES,
            )
            # The project will be specified in genai.Client, not on credentials
            _LOGGER.debug("Authorized user credentials created successfully")

            # project_id comes from config entry (user input), NOT from the credentials JSON

        else:
            _LOGGER.error(
                "Invalid credential type: %s. Must be 'service_account' "
                "or 'authorized_user'",
                credential_type,
            )
            raise ConfigEntryAuthFailed(
                f"Invalid credential type: {credential_type}. "
                "Must be 'service_account' or 'authorized_user'"
            )

    except json.JSONDecodeError as err:
        _LOGGER.error("Invalid credentials JSON: %s", err)
        raise ConfigEntryAuthFailed("Credentials JSON is invalid or malformed") from err
    except (KeyError, ValueError) as err:
        _LOGGER.error("Invalid credentials: %s", err)
        raise ConfigEntryAuthFailed("Credentials are missing required fields") from err
    except GoogleAuthError as err:
        _LOGGER.error("Google authentication error: %s", err)
        raise ConfigEntryAuthFailed(
            f"Failed to authenticate with Google: {err}"
        ) from err

    # Write credentials to a persistent temporary file for AnthropicVertex
    # We need this file to persist for the lifetime of the integration
    credentials_file = None
    try:
        # Create a temporary file for credentials
        credentials_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            dir=hass.config.config_dir,
        )
        json.dump(credentials_info, credentials_file)
        credentials_file.close()
        credentials_path = credentials_file.name

        _LOGGER.debug("Credentials written to temporary file: %s", credentials_path)

        # Set environment variable for credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        # Create Anthropic Vertex AI client
        client = AnthropicVertex(
            project_id=project_id,
            region=location,
        )

        _LOGGER.debug("AnthropicVertex client created successfully")

        # Validate connection with a simple API call
        def _validate_connection() -> None:
            """Validate connection to Vertex AI (runs in executor)."""
            try:
                # Test the connection with a simple API call
                client.messages.create(
                    model="claude-sonnet-4-5@20250929",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}],
                )
                _LOGGER.debug("Successfully validated connection to Vertex AI Claude")
            except Exception as err:
                _LOGGER.error("Failed to validate Vertex AI connection: %s", err)
                raise

        # Run validation in executor since it's a blocking operation
        await hass.async_add_executor_job(_validate_connection)

    except GoogleAuthError as err:
        _LOGGER.error("Authentication failed during connection validation: %s", err)
        # Clean up credentials file on error
        if credentials_file and os.path.exists(credentials_file.name):
            try:
                os.unlink(credentials_file.name)
            except Exception:
                pass
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
    except Exception as err:
        _LOGGER.error("Failed to connect to Vertex AI: %s", err)
        # Clean up credentials file on error
        if credentials_file and os.path.exists(credentials_file.name):
            try:
                os.unlink(credentials_file.name)
            except Exception:
                pass
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
        "credentials_path": credentials_path,
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
        # Clean up credentials file if it exists
        entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
        credentials_path = entry_data.get("credentials_path")
        if credentials_path and os.path.exists(credentials_path):
            try:
                os.unlink(credentials_path)
                _LOGGER.debug("Cleaned up credentials file: %s", credentials_path)
            except Exception as err:
                _LOGGER.warning("Failed to clean up credentials file: %s", err)

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
