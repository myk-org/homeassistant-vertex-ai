# Vertex AI Conversation for Home Assistant

A comprehensive Home Assistant integration that brings Google Cloud's Vertex AI Gemini models to your smart home. This integration provides conversation AI, text-to-speech, speech-to-text, and AI task capabilities powered by Google's latest Gemini models.

## Features

- **Conversation Agent**: Natural language conversation using Gemini 2.5 Flash and other Vertex AI models
- **Text-to-Speech (TTS)**: Generate natural-sounding speech from text using Gemini TTS models
- **Speech-to-Text (STT)**: Convert spoken audio to text with high accuracy
- **AI Tasks**: Execute complex AI-powered tasks and automation
- **Multiple Model Support**: Access various Gemini models including Flash, Pro, and specialized variants
- **Configurable Parameters**: Fine-tune temperature, top-p, top-k, and max tokens for optimal responses
- **Safety Controls**: Built-in content safety filtering with configurable thresholds
- **Cloud Integration**: Leverages Google Cloud's powerful infrastructure for reliable AI processing

## Prerequisites

Before installing this integration, you need:

1. **Google Cloud Platform (GCP) Account**
   - Active GCP account with billing enabled
   - Visit [Google Cloud Console](https://console.cloud.google.com/)

2. **GCP Project**
   - Create or select a GCP project
   - Note your Project ID (you'll need this during setup)

3. **Vertex AI API Enabled**
   - Navigate to [Vertex AI API](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com)
   - Click "Enable" for your project

4. **Service Account with Proper Permissions**
   - Service account with "Vertex AI User" role
   - JSON key file for authentication (see Configuration section)

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add the repository URL: `https://github.com/myakove/homeassistant-claude-vertex-ai`
6. Select category: "Integration"
7. Click "Add"
8. Click "Install" on the Vertex AI Conversation card
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub releases](https://github.com/myakove/homeassistant-claude-vertex-ai/releases)
2. Extract the `claude_vertex_ai_conversation` folder from the archive
3. Copy the folder to your Home Assistant `custom_components` directory:
   ```
   /config/custom_components/claude_vertex_ai_conversation/
   ```
4. Restart Home Assistant

## Configuration

### Step 1: Create a Service Account in Google Cloud

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Go to "IAM & Admin" > "Service Accounts"
4. Click "Create Service Account"
5. Provide a name (e.g., "homeassistant-claude-vertex-ai")
6. Click "Create and Continue"
7. Grant the role: "Vertex AI User"
8. Click "Continue" and then "Done"
9. Click on the newly created service account
10. Go to the "Keys" tab
11. Click "Add Key" > "Create new key"
12. Select "JSON" format
13. Click "Create" - the JSON key file will download automatically
14. Save this file securely (you'll need its contents for Home Assistant)

### Step 2: Add Integration in Home Assistant

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Vertex AI Conversation"
4. Fill in the required fields:
   - **Project ID**: Your GCP project ID (found in GCP Console)
   - **Location**: GCP region for Vertex AI (default: `us-central1`)
     - Available regions: `us-central1`, `us-east1`, `us-west1`, `europe-west1`, `asia-northeast1`, etc.
   - **Service Account JSON**: Paste the entire contents of your downloaded JSON key file
5. Click "Submit"
6. Wait for validation (the integration will verify your credentials and connection)

### Step 3: Configure Conversation Agent (Optional)

After adding the integration, you can configure individual components:

1. Go to Settings > Voice Assistants
2. Select or create an assistant
3. Choose "Vertex AI Conversation" as the conversation agent
4. Configure your preferred model and parameters

## Configuration Fields Explained

### Project ID
Your Google Cloud project identifier. Found in the GCP Console dashboard or in your service account JSON file.

### Location
The GCP region where Vertex AI API requests will be processed. Choose a region close to your Home Assistant instance for better latency:
- `us-central1` (Iowa, USA) - Default
- `us-east1` (South Carolina, USA)
- `us-west1` (Oregon, USA)
- `europe-west1` (Belgium)
- `asia-northeast1` (Tokyo, Japan)

Full list: [Vertex AI Locations](https://cloud.google.com/vertex-ai/docs/general/locations)

### Service Account JSON
The complete JSON key file content from your GCP service account. This JSON should include:
- `type`: Should be "service_account"
- `project_id`: Your GCP project ID
- `private_key`: Authentication key
- `client_email`: Service account email

Example structure:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

## Usage Examples

### Conversation Agent

Ask natural language questions through Home Assistant:

```yaml
# In automations.yaml
automation:
  - alias: "Ask Vertex AI"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door
        to: "on"
    action:
      - service: conversation.process
        data:
          agent_id: conversation.claude_vertex_ai_conversation
          text: "What should I do if someone is at my front door?"
```

### Text-to-Speech

Generate speech from text:

```yaml
# In scripts.yaml
script:
  announce_weather:
    sequence:
      - service: tts.speak
        target:
          entity_id: media_player.living_room
        data:
          media_player_entity_id: media_player.living_room
          message: "Good morning! Today's weather looks beautiful."
          options:
            voice: "en-US-Neural2-A"
```

### Voice Assistant Integration

1. Go to Settings > Voice Assistants
2. Create a new assistant or edit existing
3. Select "Vertex AI Conversation" as the Conversation Agent
4. Optionally select "Vertex AI TTS" and "Vertex AI STT"
5. Test with "Hey Google" or your wake word

## Supported Models

### Conversation Models
- `gemini-2.5-flash` (Recommended) - Fast, efficient model for conversations
- `gemini-2.5-pro` - Advanced model for complex reasoning
- `gemini-1.5-flash` - Previous generation fast model
- `gemini-1.5-pro` - Previous generation advanced model

### Text-to-Speech Models
- `gemini-2.5-flash-preview-tts` (Recommended) - Natural-sounding speech synthesis

### Speech-to-Text Models
- `gemini-2.5-flash` (Recommended) - Accurate speech recognition
- Other Gemini models with audio capabilities

### Model Parameters

You can customize model behavior:
- **Temperature** (0.0-2.0): Controls randomness. Higher = more creative, Lower = more deterministic
  - Default: 1.0
- **Top P** (0.0-1.0): Nucleus sampling threshold. Controls diversity
  - Default: 0.95
- **Top K** (1-100): Limits token selection to top K choices
  - Default: 64
- **Max Tokens**: Maximum response length
  - Default: 3000

## Troubleshooting

### Common Issues

#### Authentication Failed
**Error**: "Authentication failed" or "Invalid service account"

**Solutions**:
- Verify the service account JSON is valid and complete
- Ensure the service account has "Vertex AI User" role
- Check that the project ID matches the service account's project
- Confirm Vertex AI API is enabled in your GCP project

#### Connection Failed
**Error**: "Unable to connect to Vertex AI service"

**Solutions**:
- Check your internet connection
- Verify the selected location/region is valid
- Ensure your GCP project has billing enabled
- Check GCP quotas and limits haven't been exceeded
- Review [Vertex AI status page](https://status.cloud.google.com/)

#### Invalid Location
**Error**: "Location not available" or connection timeouts

**Solutions**:
- Use a supported Vertex AI region (see Configuration Fields above)
- Check [available regions](https://cloud.google.com/vertex-ai/docs/general/locations)
- Try default location: `us-central1`

#### Models Not Listed
**Problem**: No models appear when configuring

**Solutions**:
- Wait a few moments for the integration to load
- Ensure Vertex AI API is enabled
- Verify service account permissions
- Check Home Assistant logs for errors:
  ```
  Settings > System > Logs
  ```

#### Rate Limits or Quota Exceeded
**Error**: "Quota exceeded" or "Rate limit"

**Solutions**:
- Check your [GCP quotas](https://console.cloud.google.com/iam-admin/quotas)
- Request quota increase if needed
- Reduce request frequency in automations
- Consider upgrading your GCP plan

### Enable Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.claude_vertex_ai_conversation: debug
    google.auth: debug
```

Restart Home Assistant and check logs under Settings > System > Logs.

### Still Having Issues?

1. Check the [GitHub Issues](https://github.com/myakove/homeassistant-claude-vertex-ai/issues) page
2. Review Home Assistant logs for detailed error messages
3. Verify your GCP setup follows [Vertex AI documentation](https://cloud.google.com/vertex-ai/docs)
4. Create a new issue with:
   - Home Assistant version
   - Integration version
   - Error messages from logs
   - Steps to reproduce

## Cost Considerations

This integration uses Google Cloud Platform services which may incur costs:

- **Vertex AI API**: Charged per request and token usage
- **Pricing varies by**:
  - Model type (Flash vs Pro)
  - Input/output tokens
  - Region/location
- **Cost optimization tips**:
  - Use Flash models for routine tasks (more cost-effective)
  - Set reasonable max token limits
  - Monitor usage in GCP Console
  - Set up billing alerts

Check current pricing: [Vertex AI Pricing](https://cloud.google.com/vertex-ai/pricing)

## Privacy and Security

- **Data Processing**: Your conversations are processed by Google Cloud Platform
- **Data Location**: Processed in your selected GCP region
- **Service Account Security**: Keep your JSON key file secure and never commit to version control
- **Google's Terms**: Subject to [Google Cloud Terms of Service](https://cloud.google.com/terms)
- **Recommendation**: Use environment variables or Home Assistant secrets for storing credentials

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for [Home Assistant](https://www.home-assistant.io/)
- Powered by [Google Cloud Vertex AI](https://cloud.google.com/vertex-ai)
- Uses [Google Generative AI SDK](https://github.com/googleapis/python-genai)

## Support

- **Issues**: [GitHub Issues](https://github.com/myakove/homeassistant-claude-vertex-ai/issues)
- **Documentation**: [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- **Home Assistant Community**: [Community Forum](https://community.home-assistant.io/)

## Changelog

### Version 1.0.0
- Initial release
- Conversation agent support
- Text-to-Speech (TTS) support
- Speech-to-Text (STT) support
- AI Tasks support
- Multi-model support (Gemini 2.5 Flash, Pro, etc.)
- Configurable model parameters
- Safety settings configuration
- HACS integration

---

**Made with ❤️ for the Home Assistant community**
