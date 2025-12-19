"""Config flow for Vertex AI Conversation integration."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any

from anthropic import AnthropicVertex
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
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
    VERTEX_AI_SCOPES,
)

_LOGGER = logging.getLogger(__name__)

# Error messages
ERROR_INVALID_JSON = "invalid_json"
ERROR_MISSING_FIELDS = "missing_fields"
ERROR_INVALID_TYPE = "invalid_type"
ERROR_CONNECTION_FAILED = "connection_failed"
ERROR_UNKNOWN = "unknown"

# Required fields for different credential types
REQUIRED_SERVICE_ACCOUNT_FIELDS = [
    "type",
    "project_id",
    "private_key",
    "client_email",
]

REQUIRED_AUTHORIZED_USER_FIELDS = [
    "type",
    "client_id",
    "client_secret",
    "refresh_token",
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
                vol.Required(CONF_LOCATION): TextSelector(
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

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
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
                        CONF_SERVICE_ACCOUNT_JSON: user_input[
                            CONF_SERVICE_ACCOUNT_JSON
                        ],
                    },
                )
            else:
                errors["base"] = validation_result["error"]

        assert self._reauth_entry is not None

        # Show the form with current values
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_PROJECT_ID,
                    default=self._reauth_entry.data[CONF_PROJECT_ID],
                ): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                    )
                ),
                vol.Required(
                    CONF_LOCATION,
                    default=self._reauth_entry.data.get(
                        CONF_LOCATION, DEFAULT_LOCATION
                    ),
                ): TextSelector(
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
                credentials_info = json.loads(user_input[CONF_SERVICE_ACCOUNT_JSON])
            except (json.JSONDecodeError, ValueError):
                return {"valid": False, "error": ERROR_INVALID_JSON}

            # Validate it's a dictionary
            if not isinstance(credentials_info, dict):
                return {"valid": False, "error": ERROR_INVALID_JSON}

            # Determine credential type and validate fields
            credential_type = credentials_info.get("type")

            if credential_type == "service_account":
                # Check service account required fields
                missing_fields = [
                    field
                    for field in REQUIRED_SERVICE_ACCOUNT_FIELDS
                    if field not in credentials_info
                ]
                if missing_fields:
                    _LOGGER.error(
                        "Missing required fields in service account JSON: %s",
                        ", ".join(missing_fields),
                    )
                    return {"valid": False, "error": ERROR_MISSING_FIELDS}

                # Create service account credentials
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_info,
                    scopes=VERTEX_AI_SCOPES,
                )
                project_id = user_input[CONF_PROJECT_ID]

            elif credential_type == "authorized_user":
                # Check authorized_user required fields
                missing_fields = [
                    field
                    for field in REQUIRED_AUTHORIZED_USER_FIELDS
                    if field not in credentials_info
                ]
                if missing_fields:
                    _LOGGER.error(
                        "Missing required fields in authorized_user JSON: %s",
                        ", ".join(missing_fields),
                    )
                    return {"valid": False, "error": ERROR_MISSING_FIELDS}

                # For authorized_user type:
                # Remove quota_project_id from the dict to avoid conflicts
                creds_info_clean = {k: v for k, v in credentials_info.items() if k != "quota_project_id"}

                # Create credentials without quota_project_id
                # The project will be specified in genai.Client, not on credentials
                credentials = Credentials.from_authorized_user_info(
                    creds_info_clean,
                    scopes=VERTEX_AI_SCOPES,
                )

                # ALWAYS use the user-provided project_id from the form
                project_id = user_input[CONF_PROJECT_ID]

            else:
                _LOGGER.error(
                    "Invalid credential type: %s. Must be 'service_account' "
                    "or 'authorized_user'",
                    credential_type,
                )
                return {"valid": False, "error": ERROR_INVALID_TYPE}

            # Test the connection
            try:
                # Write credentials to a temporary file for AnthropicVertex
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".json",
                    delete=False,
                ) as temp_file:
                    json.dump(credentials_info, temp_file)
                    temp_credentials_path = temp_file.name

                try:
                    # Set environment variable for credentials
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_credentials_path

                    # Create Anthropic Vertex AI client
                    client = AnthropicVertex(
                        project_id=project_id,
                        region=user_input[CONF_LOCATION],
                    )

                    # Test the connection with a simple API call
                    await self.hass.async_add_executor_job(
                        lambda: client.messages.create(
                            model="claude-sonnet-4-5@20250929",
                            max_tokens=10,
                            messages=[{"role": "user", "content": "test"}],
                        )
                    )

                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_credentials_path)
                    except Exception:
                        pass

            except Exception as err:
                _LOGGER.error("Failed to connect to Vertex AI with Claude: %s", err)
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


# NOTE: Sub-entry flows are commented out for now as they conflict with the main config flow.
# Sub-entries should be handled through the options flow or as separate platforms.
# This class was causing the "not_implemented" error by overriding the main ConfigFlow.
#
# class VertexAISubEntryFlow(ConfigFlow, domain=DOMAIN):
#     """Handle sub-entry config flow for conversation, TTS, STT, and AI task."""
#
#     VERSION = 1
#
#     def __init__(self) -> None:
#         """Initialize the sub-entry flow."""
#         self._parent_entry: ConfigEntry | None = None
#         self._subentry_type: str | None = None
#
#     async def async_step_conversation(
#         self, user_input: dict[str, Any] | None = None
#     ) -> ConfigFlowResult:
#         """Handle conversation sub-entry."""
#         self._subentry_type = SUBENTRY_CONVERSATION
#         return await self._handle_subentry(user_input, "Conversation Agent")
#
#     async def async_step_tts(
#         self, user_input: dict[str, Any] | None = None
#     ) -> ConfigFlowResult:
#         """Handle TTS sub-entry."""
#         self._subentry_type = SUBENTRY_TTS
#         return await self._handle_subentry(user_input, "Text-to-Speech")
#
#     async def async_step_stt(
#         self, user_input: dict[str, Any] | None = None
#     ) -> ConfigFlowResult:
#         """Handle STT sub-entry."""
#         self._subentry_type = SUBENTRY_STT
#         return await self._handle_subentry(user_input, "Speech-to-Text")
#
#     async def async_step_ai_task_data(
#         self, user_input: dict[str, Any] | None = None
#     ) -> ConfigFlowResult:
#         """Handle AI task sub-entry."""
#         self._subentry_type = SUBENTRY_AI_TASK
#         return await self._handle_subentry(user_input, "AI Task")
#
#     async def _handle_subentry(
#         self, user_input: dict[str, Any] | None, title_prefix: str
#     ) -> ConfigFlowResult:
#         """Handle sub-entry creation."""
#         if user_input is not None:
#             # Get parent entry from context
#             parent_entry_id = self.context.get("parent_entry_id")
#             if not parent_entry_id:
#                 return self.async_abort(reason="missing_parent")
#
#             parent_entry = self.hass.config_entries.async_get_entry(parent_entry_id)
#             if not parent_entry:
#                 return self.async_abort(reason="parent_not_found")
#
#             # Create unique ID for this sub-entry
#             unique_id = f"{parent_entry.entry_id}_{self._subentry_type}_{user_input.get(CONF_NAME, '')}"
#             await self.async_set_unique_id(unique_id)
#             self._abort_if_unique_id_configured()
#
#             return self.async_create_entry(
#                 title=f"{title_prefix}: {user_input.get(CONF_NAME, 'Default')}",
#                 data={
#                     "parent_entry_id": parent_entry_id,
#                     "subentry_type": self._subentry_type,
#                     **user_input,
#                 },
#             )
#
#         # Show form for sub-entry
#         data_schema = vol.Schema(
#             {
#                 vol.Optional(CONF_NAME, default="Default"): TextSelector(
#                     TextSelectorConfig(
#                         type=TextSelectorType.TEXT,
#                     )
#                 ),
#             }
#         )
#
#         return self.async_show_form(
#             step_id=self._subentry_type or "init",
#             data_schema=data_schema,
#         )
