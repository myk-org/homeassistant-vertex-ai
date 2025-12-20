# Claude Vertex AI Conversation for Home Assistant

A Home Assistant integration that brings Anthropic's Claude AI models to your smart home via Google Cloud Vertex AI. This integration provides conversation AI and AI task capabilities powered by Claude's advanced language models through Google Cloud's infrastructure.

## Overview

This integration is based on the official Home Assistant [Anthropic component](https://www.home-assistant.io/integrations/anthropic/) but adapted to use Google Cloud Vertex AI instead of Anthropic's API directly. This allows you to leverage Claude models through your existing Google Cloud Platform infrastructure.

## Features

- **Conversation Agent**: Natural language conversation using Claude models via Vertex AI
- **AI Tasks**: Execute complex AI-powered tasks and automation
- **Tool Calling**: Claude can interact with your Home Assistant devices and services
- **Extended Thinking**: Enable deeper reasoning for complex queries
- **Web Search**: Allow Claude to search the web for up-to-date information (when supported)
- **Multiple Model Support**: Access various Claude models including Sonnet and Opus variants
- **Configurable Parameters**: Fine-tune temperature, max tokens, and thinking settings for optimal responses

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
   - Ensure Claude models are available in your selected region

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
8. Click "Install" on the Claude Vertex AI Conversation card
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
5. Provide a name (e.g., "homeassistant-claude-vertex")
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
3. Search for "Claude Vertex AI Conversation"
4. Fill in the required fields:
   - **Project ID**: Your GCP project ID (found in GCP Console)
   - **Location**: GCP region where Claude models are available (e.g., `us-east5`)
     - Check [Vertex AI Model Garden](https://console.cloud.google.com/vertex-ai/model-garden) for Claude availability in your region
   - **Service Account JSON**: Paste the entire contents of your downloaded JSON key file
5. Click "Submit"
6. Wait for validation (the integration will verify your credentials and connection)

### Step 3: Configure Conversation Agent

After adding the integration:

1. Go to Settings > Voice Assistants
2. Select or create an assistant
3. Choose "Claude Vertex AI Conversation" as the conversation agent
4. Configure your preferred model and parameters

## Configuration Fields Explained

### Project ID
Your Google Cloud project identifier. Found in the GCP Console dashboard or in your service account JSON file.

### Location
The GCP region where Vertex AI API requests will be processed. Claude models are available in specific regions:
- `us-east5` (Columbus, USA) - Recommended for Claude models
- `europe-west1` (Belgium) - Check availability
- `asia-southeast1` (Singapore) - Check availability

**Important**: Not all Vertex AI regions support Claude models. Check [Vertex AI Model Garden](https://console.cloud.google.com/vertex-ai/model-garden) to verify Claude availability in your preferred region.

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

## Available Models

Claude models available through Vertex AI (availability varies by region):

The following models are available as documented in the [official Google Cloud Vertex AI documentation](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/claude):

### Claude 4.5 Series
- `claude-haiku-4-5` - Fast and efficient model (Recommended for routine tasks)
- `claude-sonnet-4-5` - Balanced performance and capability (Recommended for most use cases)
- `claude-opus-4-5` - Most capable model for complex tasks

### Claude 4.1 Series
- `claude-opus-4-1` - Advanced model for complex reasoning

### Claude 4 Series
- `claude-opus-4` - Capable model for complex tasks
- `claude-sonnet-4` - Balanced performance model

### Claude 3.5 Series
- `claude-3-5-haiku` - Fast and efficient model

### Claude 3 Series
- `claude-3-haiku` - Fastest model for simple tasks

**Note**: Model availability depends on your GCP region and Vertex AI access. Check the [Vertex AI Model Garden](https://console.cloud.google.com/vertex-ai/model-garden) for the latest available models in your region.

**Important**: Unlike the direct Anthropic API, Vertex AI does NOT use the `-latest` suffix for model names. Use the exact model names listed above.

### Model Parameters

Customize model behavior in the integration options:

- **Temperature** (0.0-1.0): Controls randomness
  - Lower (0.0-0.3): More focused and deterministic
  - Medium (0.4-0.7): Balanced creativity
  - Higher (0.8-1.0): More creative and varied
  - Default: 1.0

- **Max Tokens**: Maximum response length (1-4096)
  - Default: 1024
  - Increase for longer, detailed responses
  - Decrease to limit token usage and costs

- **Recommended Safe Prompt**: Add safety instructions to prompts
  - Default: Enabled
  - Helps prevent harmful or inappropriate responses

- **Extended Thinking**: Enable Claude's extended reasoning capabilities
  - Default: Disabled
  - Useful for complex problem-solving tasks
  - May increase response time and token usage

## Usage Examples

### Conversation Agent

Ask natural language questions through Home Assistant:

```yaml
# In automations.yaml
automation:
  - alias: "Ask Claude about front door"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door
        to: "on"
    action:
      - service: conversation.process
        data:
          agent_id: conversation.claude_vertex_ai_conversation
          text: "Someone is at my front door. What actions should I take?"
```

### AI Tasks

Use Claude for complex reasoning tasks:

```yaml
# In scripts.yaml
script:
  analyze_energy_usage:
    sequence:
      - service: anthropic.generate_content
        data:
          agent_id: conversation.claude_vertex_ai_conversation
          prompt: "Analyze my home's energy usage patterns and suggest optimizations"
        response_variable: analysis
      - service: notify.mobile_app
        data:
          message: "{{ analysis.content }}"
```

### Voice Assistant Integration

1. Go to Settings > Voice Assistants
2. Create a new assistant or edit existing
3. Select "Claude Vertex AI Conversation" as the Conversation Agent
4. Test with your wake word or voice interface

### Using Tool Calling

Claude can control your Home Assistant devices:

```yaml
# Example automation that allows Claude to control lights
automation:
  - alias: "Claude controls bedroom lights"
    trigger:
      - platform: conversation
        command: "turn on bedroom lights to 50% brightness"
    action:
      - service: conversation.process
        data:
          agent_id: conversation.claude_vertex_ai_conversation
          text: "{{ trigger.text }}"
```

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

#### Model Not Available
**Error**: "Model not found" or "Model not available in region"

**Solutions**:
- Check if Claude models are available in your selected region
- Try using `us-east5` region which has broad Claude model support
- Visit [Vertex AI Model Garden](https://console.cloud.google.com/vertex-ai/model-garden) to verify model availability
- Ensure you have access to Anthropic models through your GCP account

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
    anthropic: debug
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
  - Model type (Haiku, Sonnet, Opus)
  - Input/output tokens
  - Region/location
  - Whether extended thinking is enabled
- **Cost optimization tips**:
  - Use Haiku models for routine tasks (most cost-effective)
  - Use Sonnet for balanced performance and cost
  - Reserve Opus for complex reasoning tasks
  - Set reasonable max token limits
  - Disable extended thinking unless needed
  - Monitor usage in GCP Console
  - Set up billing alerts

Check current pricing:
- [Vertex AI Pricing](https://cloud.google.com/vertex-ai/pricing)
- [Anthropic Pricing on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/pricing)

## Privacy and Security

- **Data Processing**: Your conversations are processed by Google Cloud Platform using Anthropic's Claude models
- **Data Location**: Processed in your selected GCP region
- **Service Account Security**: Keep your JSON key file secure and never commit to version control
- **Google's Terms**: Subject to [Google Cloud Terms of Service](https://cloud.google.com/terms)
- **Anthropic's Terms**: Subject to [Anthropic's Terms](https://www.anthropic.com/legal/consumer-terms)
- **Recommendation**: Use environment variables or Home Assistant secrets for storing credentials

## Differences from Official Anthropic Integration

This integration differs from the official Home Assistant Anthropic component:

- **API Endpoint**: Uses Google Cloud Vertex AI instead of Anthropic's direct API
- **Authentication**: Requires GCP service account instead of Anthropic API key
- **Billing**: Costs are billed through your Google Cloud account
- **Regional Deployment**: Models run in specific GCP regions
- **Feature Set**: Based on the same core functionality as the official component

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Credits and Acknowledgments

- **Based on**: [Home Assistant Anthropic Integration](https://www.home-assistant.io/integrations/anthropic/)
- **Original Authors**: Home Assistant Core Team
- **Claude Models**: Developed by [Anthropic](https://www.anthropic.com/)
- **Infrastructure**: Powered by [Google Cloud Vertex AI](https://cloud.google.com/vertex-ai)
- **Built for**: [Home Assistant](https://www.home-assistant.io/)

Special thanks to the Home Assistant community and the developers of the official Anthropic integration.

## Support

- **Issues**: [GitHub Issues](https://github.com/myakove/homeassistant-claude-vertex-ai/issues)
- **Vertex AI Documentation**: [Vertex AI Docs](https://cloud.google.com/vertex-ai/docs)
- **Anthropic Documentation**: [Anthropic Docs](https://docs.anthropic.com/)
- **Home Assistant Community**: [Community Forum](https://community.home-assistant.io/)
- **Official Anthropic Integration**: [HA Anthropic Docs](https://www.home-assistant.io/integrations/anthropic/)

## Changelog

### Version 1.0.0
- Initial release based on Home Assistant Anthropic integration
- Conversation agent support with Claude models via Vertex AI
- AI Tasks support
- Tool calling capabilities
- Extended thinking support
- Web search support (when available)
- Multi-model support (Claude 3.5 Sonnet, Haiku, Opus, etc.)
- Configurable model parameters
- HACS integration

---

**Made with ❤️ for the Home Assistant community**
