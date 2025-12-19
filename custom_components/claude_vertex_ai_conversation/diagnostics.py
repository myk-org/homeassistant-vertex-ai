"""Diagnostics support for Vertex AI Conversation."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_SERVICE_ACCOUNT_JSON

TO_REDACT = {CONF_SERVICE_ACCOUNT_JSON}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    diagnostics_data = {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": entry.options,
        },
    }

    # Include subentries information if available
    if entry.runtime_data and hasattr(entry.runtime_data, "subentries"):
        subentries_info = []
        for subentry in entry.runtime_data.subentries:
            subentries_info.append(
                {
                    "type": subentry.type,
                    "data": async_redact_data(subentry.data, TO_REDACT),
                }
            )
        diagnostics_data["subentries"] = subentries_info

    return diagnostics_data
