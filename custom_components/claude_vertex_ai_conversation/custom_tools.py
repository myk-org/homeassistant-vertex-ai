"""Custom tools support for Claude conversation."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
import yaml

from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.helpers.template import Template as HATemplate

_LOGGER = logging.getLogger(__name__)

# Schema for a single custom tool definition
TOOL_SCHEMA = vol.Schema(
    {
        vol.Required("spec"): {
            vol.Required("name"): str,
            vol.Required("description"): str,
            vol.Required("parameters"): dict,
        },
        vol.Required("function"): {
            vol.Required("type"): vol.In(["script"]),
            vol.Optional("sequence"): list,
        },
    }
)

TOOLS_SCHEMA = vol.Schema([TOOL_SCHEMA])


class CustomTool(llm.Tool):
    """A custom tool that can call Home Assistant services."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: vol.Schema,
        function_config: dict[str, Any],
        hass: HomeAssistant,
    ) -> None:
        """Initialize the custom tool."""
        self._name = name
        self._description = description
        self._parameters = parameters
        self._function_config = function_config
        self._hass = hass

    @property
    def name(self) -> str:
        """Return tool name."""
        return self._name

    @property
    def description(self) -> str:
        """Return tool description."""
        return self._description

    @property
    def parameters(self) -> vol.Schema:
        """Return tool parameters schema."""
        return self._parameters

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> Any:
        """Execute the custom tool."""
        func_type = self._function_config.get("type")

        if func_type == "script":
            return await self._execute_script(tool_input.tool_args)

        return {"error": f"Unknown function type: {func_type}"}

    async def _execute_script(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a script-type function (sequence of service calls)."""
        sequence = self._function_config.get("sequence", [])
        results = []

        for step in sequence:
            service_full = step.get("service", "")
            if "/" in service_full:
                domain, service = service_full.split("/", 1)
            elif "." in service_full:
                domain, service = service_full.split(".", 1)
            else:
                _LOGGER.warning("Invalid service format: %s", service_full)
                continue

            # Validate service exists
            if not self._hass.services.has_service(domain, service):
                _LOGGER.error("Service %s.%s does not exist", domain, service)
                results.append({
                    "service": service_full,
                    "success": False,
                    "error": f"Service {service_full} does not exist"
                })
                continue

            # Process data with Jinja2 templates
            data = step.get("data", {})
            processed_data = self._process_templates(data, args)

            # Handle target
            target = step.get("target", {})
            processed_target = self._process_templates(target, args)

            # Call the service with timeout
            try:
                await asyncio.wait_for(
                    self._hass.services.async_call(
                        domain,
                        service,
                        processed_data,
                        target=processed_target if processed_target else None,
                        blocking=True,
                    ),
                    timeout=30.0  # 30 second timeout
                )
                results.append({"service": service_full, "success": True})
            except asyncio.TimeoutError:
                _LOGGER.error("Service %s timed out after 30 seconds", service_full)
                results.append({
                    "service": service_full,
                    "success": False,
                    "error": "Service call timed out"
                })
            except Exception as err:
                _LOGGER.error("Error calling service %s: %s", service_full, err)
                results.append(
                    {"service": service_full, "success": False, "error": str(err)}
                )

        return {"results": results}

    def _process_templates(self, data: Any, args: dict[str, Any]) -> Any:
        """Process Jinja2 templates in data using Home Assistant's sandboxed renderer."""
        if isinstance(data, str):
            if "{{" in data or "{%" in data:
                # Use HA's sandboxed template
                template = HATemplate(data, self._hass)
                rendered = template.async_render(args, limited=True)
                # Try to parse as YAML for complex types
                try:
                    return yaml.safe_load(rendered)
                except yaml.YAMLError:
                    return rendered
            return data
        elif isinstance(data, dict):
            return {k: self._process_templates(v, args) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._process_templates(item, args) for item in data]
        return data


def parse_custom_tools(
    hass: HomeAssistant,
    yaml_config: str,
) -> list[CustomTool]:
    """Parse YAML configuration and return list of CustomTool objects."""
    if not yaml_config or not yaml_config.strip():
        return []

    try:
        tools_config = yaml.safe_load(yaml_config)
        if not tools_config:
            return []

        # Validate against schema
        validated = TOOLS_SCHEMA(tools_config)

        custom_tools = []
        seen_names: set[str] = set()

        # Reserved tool names that shouldn't be overridden
        RESERVED_NAMES = {"web_search"}

        for tool_def in validated:
            spec = tool_def["spec"]
            func = tool_def["function"]

            tool_name = spec["name"]

            # Check for reserved names
            if tool_name in RESERVED_NAMES:
                _LOGGER.error(
                    "Tool name '%s' is reserved and cannot be used",
                    tool_name
                )
                continue

            # Check for duplicate names
            if tool_name in seen_names:
                _LOGGER.error(
                    "Duplicate tool name '%s' found, skipping",
                    tool_name
                )
                continue
            seen_names.add(tool_name)

            # Convert parameters dict to voluptuous schema
            params_schema = _convert_parameters_to_schema(spec["parameters"])

            custom_tools.append(
                CustomTool(
                    name=spec["name"],
                    description=spec["description"],
                    parameters=params_schema,
                    function_config=func,
                    hass=hass,
                )
            )

        _LOGGER.info("Loaded %d custom tool(s)", len(custom_tools))
        return custom_tools

    except yaml.YAMLError as err:
        _LOGGER.error("Invalid YAML in custom tools: %s", err)
        return []
    except vol.Invalid as err:
        _LOGGER.error("Invalid custom tools schema: %s", err)
        return []
    except Exception as err:
        _LOGGER.error("Unexpected error parsing custom tools: %s", err)
        return []


def _convert_parameters_to_schema(params: dict) -> vol.Schema:
    """Convert OpenAI-style parameters to voluptuous schema."""
    schema_dict = {}
    properties = params.get("properties", {})
    required = params.get("required", [])

    for prop_name, prop_def in properties.items():
        prop_type = prop_def.get("type", "string")

        # Map JSON schema types to Python types
        type_map = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        python_type = type_map.get(prop_type, str)

        if prop_name in required:
            schema_dict[
                vol.Required(prop_name, description=prop_def.get("description", ""))
            ] = python_type
        else:
            schema_dict[
                vol.Optional(prop_name, description=prop_def.get("description", ""))
            ] = python_type

    return vol.Schema(schema_dict)
