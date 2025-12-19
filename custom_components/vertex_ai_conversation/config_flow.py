"""Config flow for Vertex AI Conversation integration."""

from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.oauth2 import service_account
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_LOCATION,
    CONF_PROJECT_ID,
    CONF_SERVICE_ACCOUNT_JSON,
    DEFAULT_LOCATION,
    DOMAIN,
    SUBENTRY_AI_TASK,
    SUBENTRY_CONVERSATION,
    SUBENTRY_STT,
    SUBENTRY_TTS,
    VERTEX_AI_SCOPES,
)

_LOGGER = logging.getLogger(__name__)

# Error messages
ERROR_INVALID_JSON = "invalid_json"
ERROR_MISSING_FIELDS = "missing_fields"
ERROR_INVALID_TYPE = "invalid_type"
ERROR_CONNECTION_FAILED = "connection_failed"
ERROR_UNKNOWN = "unknown"

# Required fields in service account JSON
REQUIRED_SERVICE_ACCOUNT_FIELDS = [
    "type",
    "project_id",
    "private_key",
    "client_email",
]


class VertexAIConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vertex AI Conversation."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the input
            validation_result = await self._validate_input(user_input)

            if validation_result["valid"]:
                # Create a unique ID based on project_id
                await self.async_set_unique_id(user_input[CONF_PROJECT_ID])
                self._abort_if_unique_id_configured()

                # Create the config entry
                return self.async_create_entry(
                    title=f"Vertex AI ({user_input[CONF_PROJECT_ID]})",
                    data=user_input,
                )
            else:
                errors["base"] = validation_result["error"]

        # Show the form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_PROJECT_ID): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_LOCATION, default=DEFAULT_LOCATION): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_SERVICE_ACCOUNT_JSON): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                        multiline=True,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "docs_url": "https://cloud.google.com/iam/docs/service-accounts-create"
            },
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth flow."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the new credentials
            validation_result = await self._validate_input(user_input)

            if validation_result["valid"]:
                assert self._reauth_entry is not None

                # Update the entry with new credentials
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data={
                        **self._reauth_entry.data,
                        CONF_SERVICE_ACCOUNT_JSON: user_input[CONF_SERVICE_ACCOUNT_JSON],
                    },
                )
            else:
                errors["base"] = validation_result["error"]

        assert self._reauth_entry is not None

        # Show the form with current values
        data_schema = vol.Schema(
            {
                vol.Required(CONF_PROJECT_ID, default=self._reauth_entry.data[CONF_PROJECT_ID]): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_LOCATION, default=self._reauth_entry.data.get(CONF_LOCATION, DEFAULT_LOCATION)): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                    )
                ),
                vol.Required(CONF_SERVICE_ACCOUNT_JSON): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                        multiline=True,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "project_id": self._reauth_entry.data[CONF_PROJECT_ID]
            },
        )

    async def _validate_input(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Validate user input.

        Returns a dict with keys:
        - valid: bool indicating if validation passed
        - error: str error code if validation failed
        """
        try:
            # Parse the JSON
            try:
                service_account_info = json.loads(user_input[CONF_SERVICE_ACCOUNT_JSON])
            except (json.JSONDecodeError, ValueError):
                return {"valid": False, "error": ERROR_INVALID_JSON}

            # Validate it's a dictionary
            if not isinstance(service_account_info, dict):
                return {"valid": False, "error": ERROR_INVALID_JSON}

            # Check required fields
            missing_fields = [
                field
                for field in REQUIRED_SERVICE_ACCOUNT_FIELDS
                if field not in service_account_info
            ]
            if missing_fields:
                _LOGGER.error(
                    "Missing required fields in service account JSON: %s",
                    ", ".join(missing_fields),
                )
                return {"valid": False, "error": ERROR_MISSING_FIELDS}

            # Verify type is service_account
            if service_account_info.get("type") != "service_account":
                _LOGGER.error(
                    "Invalid service account type: %s", service_account_info.get("type")
                )
                return {"valid": False, "error": ERROR_INVALID_TYPE}

            # Test the connection
            try:
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=VERTEX_AI_SCOPES,
                )

                client = genai.Client(
                    vertexai=True,
                    project=user_input[CONF_PROJECT_ID],
                    location=user_input[CONF_LOCATION],
                    credentials=credentials,
                )

                # Test the connection by listing models
                # This will raise an exception if credentials are invalid
                await self.hass.async_add_executor_job(
                    lambda: list(client.models.list(page_size=1))
                )

            except Exception as err:
                _LOGGER.error("Failed to connect to Vertex AI: %s", err)
                return {"valid": False, "error": ERROR_CONNECTION_FAILED}

            return {"valid": True, "error": ""}

        except Exception as err:
            _LOGGER.exception("Unexpected error during validation: %s", err)
            return {"valid": False, "error": ERROR_UNKNOWN}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Get the options flow for this handler."""
        return VertexAIOptionsFlowHandler(config_entry)


class VertexAIOptionsFlowHandler(OptionsFlow):
    """Handle options flow for Vertex AI Conversation."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # For now, we'll just provide a placeholder options flow
        # This can be expanded later to configure default models, etc.
        data_schema = vol.Schema({})

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )


class VertexAISubEntryFlow(ConfigFlow, domain=DOMAIN):
    """Handle sub-entry config flow for conversation, TTS, STT, and AI task."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the sub-entry flow."""
        self._parent_entry: ConfigEntry | None = None
        self._subentry_type: str | None = None

    async def async_step_conversation(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle conversation sub-entry."""
        self._subentry_type = SUBENTRY_CONVERSATION
        return await self._handle_subentry(user_input, "Conversation Agent")

    async def async_step_tts(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle TTS sub-entry."""
        self._subentry_type = SUBENTRY_TTS
        return await self._handle_subentry(user_input, "Text-to-Speech")

    async def async_step_stt(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle STT sub-entry."""
        self._subentry_type = SUBENTRY_STT
        return await self._handle_subentry(user_input, "Speech-to-Text")

    async def async_step_ai_task_data(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle AI task sub-entry."""
        self._subentry_type = SUBENTRY_AI_TASK
        return await self._handle_subentry(user_input, "AI Task")

    async def _handle_subentry(
        self, user_input: dict[str, Any] | None, title_prefix: str
    ) -> ConfigFlowResult:
        """Handle sub-entry creation."""
        if user_input is not None:
            # Get parent entry from context
            parent_entry_id = self.context.get("parent_entry_id")
            if not parent_entry_id:
                return self.async_abort(reason="missing_parent")

            parent_entry = self.hass.config_entries.async_get_entry(parent_entry_id)
            if not parent_entry:
                return self.async_abort(reason="parent_not_found")

            # Create unique ID for this sub-entry
            unique_id = f"{parent_entry.entry_id}_{self._subentry_type}_{user_input.get(CONF_NAME, '')}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"{title_prefix}: {user_input.get(CONF_NAME, 'Default')}",
                data={
                    "parent_entry_id": parent_entry_id,
                    "subentry_type": self._subentry_type,
                    **user_input,
                },
            )

        # Show form for sub-entry
        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default="Default"): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id=self._subentry_type or "init",
            data_schema=data_schema,
        )
