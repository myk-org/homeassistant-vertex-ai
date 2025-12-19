"""Constants for Vertex AI Conversation integration."""
from typing import Final

DOMAIN: Final = "vertex_ai_conversation"

# Configuration keys
CONF_PROJECT_ID: Final = "project_id"
CONF_LOCATION: Final = "location"
CONF_SERVICE_ACCOUNT_JSON: Final = "service_account_json"

# Default values
DEFAULT_LOCATION: Final = "us-central1"
DEFAULT_TIMEOUT: Final = 10000  # milliseconds

# Recommended models for Vertex AI
RECOMMENDED_CHAT_MODEL: Final = "gemini-2.5-flash"
RECOMMENDED_TTS_MODEL: Final = "gemini-2.5-flash-preview-tts"
RECOMMENDED_STT_MODEL: Final = "gemini-2.5-flash"

# Model parameter defaults
RECOMMENDED_TEMPERATURE: Final = 1.0
RECOMMENDED_TOP_P: Final = 0.95
RECOMMENDED_TOP_K: Final = 64
RECOMMENDED_MAX_TOKENS: Final = 3000

# Safety settings
RECOMMENDED_HARM_BLOCK_THRESHOLD: Final = "BLOCK_MEDIUM_AND_ABOVE"

# Subentry types
SUBENTRY_CONVERSATION: Final = "conversation"
SUBENTRY_TTS: Final = "tts"
SUBENTRY_STT: Final = "stt"
SUBENTRY_AI_TASK: Final = "ai_task_data"

# Platform types
PLATFORMS: Final = ["ai_task", "conversation", "stt", "tts"]

# Default titles
DEFAULT_CONVERSATION_TITLE: Final = "Vertex AI Conversation"
DEFAULT_TTS_TITLE: Final = "Vertex AI TTS"
DEFAULT_STT_TITLE: Final = "Vertex AI STT"
DEFAULT_AI_TASK_TITLE: Final = "Vertex AI Task"

# OAuth scopes
VERTEX_AI_SCOPES: Final = ["https://www.googleapis.com/auth/cloud-platform"]
