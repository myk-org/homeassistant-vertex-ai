"""Constants for Vertex AI Conversation integration."""
from typing import Final

DOMAIN: Final = "claude_vertex_ai_conversation"

# Configuration keys
CONF_PROJECT_ID: Final = "project_id"
CONF_LOCATION: Final = "location"
CONF_SERVICE_ACCOUNT_JSON: Final = "service_account_json"
CONF_MODEL: Final = "model"
CONF_SYSTEM_PROMPT: Final = "system_prompt"
CONF_MAX_TOKENS: Final = "max_tokens"
CONF_TEMPERATURE: Final = "temperature"

# Default values
DEFAULT_LOCATION: Final = "us-east5"
DEFAULT_TIMEOUT: Final = 10000  # milliseconds

# Recommended models for Claude via Vertex AI
RECOMMENDED_CHAT_MODEL: Final = "claude-sonnet-4-5@20250929"

# Available Claude models on Vertex AI
AVAILABLE_MODELS: Final = [
    "claude-sonnet-4-5@20250929",
    "claude-sonnet-4-20250514",
    "claude-3-5-sonnet-v2@20241022",
    "claude-3-5-haiku@20241022",
    "claude-3-opus@20240229",
    "claude-3-haiku@20240307",
]

# Model parameter defaults for Claude
RECOMMENDED_TEMPERATURE: Final = 1.0
RECOMMENDED_MAX_TOKENS: Final = 3000

# Subentry types
SUBENTRY_CONVERSATION: Final = "conversation"

# Platform types (Claude only supports conversation for now)
PLATFORMS: Final = ["conversation"]

# Default titles
DEFAULT_CONVERSATION_TITLE: Final = "Claude Conversation"

# OAuth scopes
VERTEX_AI_SCOPES: Final = ["https://www.googleapis.com/auth/cloud-platform"]
