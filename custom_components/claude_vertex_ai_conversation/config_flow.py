"""Config flow for Anthropic integration."""

from __future__ import annotations

from functools import partial
import json
import logging
import os
import re
import tempfile
from typing import Any, cast

from anthropic import AnthropicVertex
import voluptuous as vol
from voluptuous_openapi import convert

from homeassistant.components.zone import ENTITY_ID_HOME
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_LLM_HASS_API,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import llm
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TemplateSelector,
)
from homeassistant.helpers.typing import VolDictType

from .const import (
    CONF_CHAT_MODEL,
    CONF_LOCATION,
    CONF_MAX_TOKENS,
    CONF_PROJECT_ID,
    CONF_PROMPT,
    CONF_RECOMMENDED,
    CONF_SERVICE_ACCOUNT_JSON,
    CONF_TEMPERATURE,
    CONF_THINKING_BUDGET,
    CONF_WEB_SEARCH,
    CONF_WEB_SEARCH_CITY,
    CONF_WEB_SEARCH_COUNTRY,
    CONF_WEB_SEARCH_MAX_USES,
    CONF_WEB_SEARCH_REGION,
    CONF_WEB_SEARCH_TIMEZONE,
    CONF_WEB_SEARCH_USER_LOCATION,
    DEFAULT,
    DEFAULT_AI_TASK_NAME,
    DEFAULT_CONVERSATION_NAME,
    DEFAULT_LOCATION,
    DOMAIN,
    NON_THINKING_MODELS,
    WEB_SEARCH_UNSUPPORTED_MODELS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PROJECT_ID): str,
        vol.Required(CONF_LOCATION, default=DEFAULT_LOCATION): str,
        vol.Required(CONF_SERVICE_ACCOUNT_JSON): str,
    }
)

DEFAULT_CONVERSATION_OPTIONS = {
    CONF_RECOMMENDED: True,
    CONF_LLM_HASS_API: [llm.LLM_API_ASSIST],
    CONF_PROMPT: llm.DEFAULT_INSTRUCTIONS_PROMPT,
}

DEFAULT_AI_TASK_OPTIONS = {
    CONF_RECOMMENDED: True,
}


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    def setup_client() -> AnthropicVertex:
        credentials_dict = json.loads(data[CONF_SERVICE_ACCOUNT_JSON])
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as temp_file:
            json.dump(credentials_dict, temp_file)
            temp_file_path = temp_file.name

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file_path
        return AnthropicVertex(
            project_id=data[CONF_PROJECT_ID], region=data[CONF_LOCATION]
        )

    client = await hass.async_add_executor_job(setup_client)
    await hass.async_add_executor_job(
        lambda: client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=10,
            messages=[{"role": "user", "content": "test"}],
        )
    )


class AnthropicConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Anthropic."""

    VERSION = 2
    MINOR_VERSION = 3

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._async_abort_entries_match(user_input)
            try:
                await validate_input(self.hass, user_input)
            except json.JSONDecodeError:
                errors["base"] = "invalid_json"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="Claude Vertex AI",
                    data=user_input,
                    subentries=[
                        {
                            "subentry_type": "conversation",
                            "data": DEFAULT_CONVERSATION_OPTIONS,
                            "title": DEFAULT_CONVERSATION_NAME,
                            "unique_id": None,
                        },
                        {
                            "subentry_type": "ai_task_data",
                            "data": DEFAULT_AI_TASK_OPTIONS,
                            "title": DEFAULT_AI_TASK_NAME,
                            "unique_id": None,
                        },
                    ],
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors or None
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        return {
            "conversation": ConversationSubentryFlowHandler,
            "ai_task_data": ConversationSubentryFlowHandler,
        }


class ConversationSubentryFlowHandler(ConfigSubentryFlow):
    """Flow for managing conversation subentries."""

    options: dict[str, Any]

    @property
    def _is_new(self) -> bool:
        """Return if this is a new subentry."""
        return self.source == "user"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a subentry."""
        if self._subentry_type == "ai_task_data":
            self.options = DEFAULT_AI_TASK_OPTIONS.copy()
        else:
            self.options = DEFAULT_CONVERSATION_OPTIONS.copy()
        return await self.async_step_init()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle reconfiguration of a subentry."""
        self.options = self._get_reconfigure_subentry().data.copy()
        return await self.async_step_init()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Set initial options."""
        # abort if entry is not loaded
        if self._get_entry().state != ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")

        hass_apis: list[SelectOptionDict] = [
            SelectOptionDict(
                label=api.name,
                value=api.id,
            )
            for api in llm.async_get_apis(self.hass)
        ]
        if (suggested_llm_apis := self.options.get(CONF_LLM_HASS_API)) and isinstance(
            suggested_llm_apis, str
        ):
            self.options[CONF_LLM_HASS_API] = [suggested_llm_apis]

        step_schema: VolDictType = {}
        errors: dict[str, str] = {}

        if self._is_new:
            if self._subentry_type == "ai_task_data":
                default_name = DEFAULT_AI_TASK_NAME
            else:
                default_name = DEFAULT_CONVERSATION_NAME
            step_schema[vol.Required(CONF_NAME, default=default_name)] = str

        if self._subentry_type == "conversation":
            step_schema.update(
                {
                    vol.Optional(CONF_PROMPT): TemplateSelector(),
                    vol.Optional(
                        CONF_LLM_HASS_API,
                    ): SelectSelector(
                        SelectSelectorConfig(options=hass_apis, multiple=True)
                    ),
                }
            )

        step_schema[
            vol.Required(
                CONF_RECOMMENDED, default=self.options.get(CONF_RECOMMENDED, False)
            )
        ] = bool

        if user_input is not None:
            if not user_input.get(CONF_LLM_HASS_API):
                user_input.pop(CONF_LLM_HASS_API, None)

            if user_input[CONF_RECOMMENDED]:
                if not errors:
                    if self._is_new:
                        return self.async_create_entry(
                            title=user_input.pop(CONF_NAME),
                            data=user_input,
                        )
                    return self.async_update_and_abort(
                        self._get_entry(),
                        self._get_reconfigure_subentry(),
                        data=user_input,
                    )
            else:
                self.options.update(user_input)
                if (
                    CONF_LLM_HASS_API in self.options
                    and CONF_LLM_HASS_API not in user_input
                ):
                    self.options.pop(CONF_LLM_HASS_API)
                if not errors:
                    return await self.async_step_advanced()

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(step_schema), self.options
            ),
            errors=errors or None,
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Manage advanced options."""
        errors: dict[str, str] = {}

        step_schema: VolDictType = {
            vol.Optional(
                CONF_CHAT_MODEL,
                default=DEFAULT[CONF_CHAT_MODEL],
            ): SelectSelector(
                SelectSelectorConfig(
                    options=await self._get_model_list(), custom_value=True
                )
            ),
            vol.Optional(
                CONF_MAX_TOKENS,
                default=DEFAULT[CONF_MAX_TOKENS],
            ): int,
            vol.Optional(
                CONF_TEMPERATURE,
                default=DEFAULT[CONF_TEMPERATURE],
            ): NumberSelector(NumberSelectorConfig(min=0, max=1, step=0.05)),
        }

        if user_input is not None:
            self.options.update(user_input)

            if not errors:
                return await self.async_step_model()

        return self.async_show_form(
            step_id="advanced",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(step_schema), self.options
            ),
            errors=errors,
        )

    async def async_step_model(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Manage model-specific options."""
        errors: dict[str, str] = {}

        step_schema: VolDictType = {}

        model = self.options[CONF_CHAT_MODEL]

        if not model.startswith(tuple(NON_THINKING_MODELS)):
            step_schema[
                vol.Optional(
                    CONF_THINKING_BUDGET, default=DEFAULT[CONF_THINKING_BUDGET]
                )
            ] = vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        max=self.options.get(CONF_MAX_TOKENS, DEFAULT[CONF_MAX_TOKENS]),
                    )
                ),
                vol.Coerce(int),
            )
        else:
            self.options.pop(CONF_THINKING_BUDGET, None)

        if not model.startswith(tuple(WEB_SEARCH_UNSUPPORTED_MODELS)):
            step_schema.update(
                {
                    vol.Optional(
                        CONF_WEB_SEARCH,
                        default=DEFAULT[CONF_WEB_SEARCH],
                    ): bool,
                    vol.Optional(
                        CONF_WEB_SEARCH_MAX_USES,
                        default=DEFAULT[CONF_WEB_SEARCH_MAX_USES],
                    ): int,
                    vol.Optional(
                        CONF_WEB_SEARCH_USER_LOCATION,
                        default=DEFAULT[CONF_WEB_SEARCH_USER_LOCATION],
                    ): bool,
                }
            )
        else:
            self.options.pop(CONF_WEB_SEARCH, None)
            self.options.pop(CONF_WEB_SEARCH_MAX_USES, None)
            self.options.pop(CONF_WEB_SEARCH_USER_LOCATION, None)

        self.options.pop(CONF_WEB_SEARCH_CITY, None)
        self.options.pop(CONF_WEB_SEARCH_REGION, None)
        self.options.pop(CONF_WEB_SEARCH_COUNTRY, None)
        self.options.pop(CONF_WEB_SEARCH_TIMEZONE, None)

        if not step_schema:
            user_input = {}

        if user_input is not None:
            if user_input.get(CONF_WEB_SEARCH, DEFAULT[CONF_WEB_SEARCH]) and not errors:
                if user_input.get(
                    CONF_WEB_SEARCH_USER_LOCATION,
                    DEFAULT[CONF_WEB_SEARCH_USER_LOCATION],
                ):
                    user_input.update(await self._get_location_data())

            self.options.update(user_input)

            if not errors:
                if self._is_new:
                    return self.async_create_entry(
                        title=self.options.pop(CONF_NAME),
                        data=self.options,
                    )

                return self.async_update_and_abort(
                    self._get_entry(),
                    self._get_reconfigure_subentry(),
                    data=self.options,
                )

        return self.async_show_form(
            step_id="model",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(step_schema), self.options
            ),
            errors=errors or None,
            last_step=True,
        )

    async def _get_model_list(self) -> list[SelectOptionDict]:
        """Get list of available models."""
        # Return default model list for Vertex AI
        # Models from: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/claude
        model_options: list[SelectOptionDict] = [
            SelectOptionDict(label="Claude Haiku 4.5", value="claude-haiku-4-5"),
            SelectOptionDict(label="Claude Sonnet 4.5", value="claude-sonnet-4-5"),
            SelectOptionDict(label="Claude Opus 4.5", value="claude-opus-4-5"),
            SelectOptionDict(label="Claude Opus 4.1", value="claude-opus-4-1"),
            SelectOptionDict(label="Claude Opus 4", value="claude-opus-4"),
            SelectOptionDict(label="Claude Sonnet 4", value="claude-sonnet-4"),
            SelectOptionDict(label="Claude 3.5 Haiku", value="claude-3-5-haiku"),
            SelectOptionDict(label="Claude 3 Haiku", value="claude-3-haiku"),
        ]
        return model_options

    async def _get_location_data(self) -> dict[str, str]:
        """Get approximate location data of the user."""
        location_data: dict[str, str] = {}
        zone_home = self.hass.states.get(ENTITY_ID_HOME)
        if zone_home is not None:

            def setup_client() -> AnthropicVertex:
                entry_data = self._get_entry().data
                credentials_dict = json.loads(entry_data[CONF_SERVICE_ACCOUNT_JSON])
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as temp_file:
                    json.dump(credentials_dict, temp_file)
                    temp_file_path = temp_file.name

                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file_path
                return AnthropicVertex(
                    project_id=entry_data[CONF_PROJECT_ID],
                    region=entry_data[CONF_LOCATION],
                )

            client = await self.hass.async_add_executor_job(setup_client)
            location_schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_WEB_SEARCH_CITY,
                        description="Free text input for the city, e.g. `San Francisco`",
                    ): str,
                    vol.Optional(
                        CONF_WEB_SEARCH_REGION,
                        description="Free text input for the region, e.g. `California`",
                    ): str,
                }
            )
            response = await self.hass.async_add_executor_job(
                lambda: client.messages.create(
                    model=cast(str, DEFAULT[CONF_CHAT_MODEL]),
                    messages=[
                        {
                            "role": "user",
                            "content": "Where are the following coordinates located: "
                            f"({zone_home.attributes[ATTR_LATITUDE]},"
                            f" {zone_home.attributes[ATTR_LONGITUDE]})? Please respond "
                            "only with a JSON object using the following schema:\n"
                            f"{convert(location_schema)}",
                        },
                        {
                            "role": "assistant",
                            "content": "{",  # hints the model to skip any preamble
                        },
                    ],
                    max_tokens=cast(int, DEFAULT[CONF_MAX_TOKENS]),
                )
            )
            _LOGGER.debug("Model response: %s", response.content)
            from anthropic.types import TextBlock

            location_data = location_schema(
                json.loads(
                    "{"
                    + "".join(
                        block.text
                        for block in response.content
                        if isinstance(block, TextBlock)
                    )
                )
                or {}
            )

        if self.hass.config.country:
            location_data[CONF_WEB_SEARCH_COUNTRY] = self.hass.config.country
        location_data[CONF_WEB_SEARCH_TIMEZONE] = self.hass.config.time_zone

        _LOGGER.debug("Location data: %s", location_data)

        return location_data
