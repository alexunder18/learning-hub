# HomeSchool — AI Provider Configuration

HomeSchool supports multiple AI providers for generating lesson content. Choose the one that fits your setup.

## Supported Providers

### 1. Claude Code CLI (mode: `cli`)

**Best for:** Users with an active Anthropic Max or Pro subscription who already have Claude Code installed.

- **Requirements:** Claude Code CLI installed and authenticated
- **Cost:** Included in Max/Pro subscription
- **Setup:**
  ```json
  {
    "mode": "cli",
    "provider": "claude-code",
    "model": "claude-opus-4-6"
  }
  ```

### 2. Anthropic API (mode: `api`)

**Best for:** Users who want direct API access with pay-per-use billing.

- **Requirements:** Anthropic API key
- **Cost:** Pay per token
- **Setup:**
  ```json
  {
    "mode": "api",
    "provider": "anthropic",
    "model": "claude-sonnet-4-6",
    "api_key": "sk-ant-..."
  }
  ```

### 3. OpenAI API (mode: `api`)

**Best for:** Users with an OpenAI account.

- **Requirements:** OpenAI API key
- **Cost:** Pay per token
- **Setup:**
  ```json
  {
    "mode": "api",
    "provider": "openai",
    "model": "gpt-4o",
    "api_key": "sk-..."
  }
  ```

### 4. Ollama (mode: `api`)

**Best for:** Users who want free, local, offline AI. No account or API key needed.

- **Requirements:** [Ollama](https://ollama.com) installed and running locally
- **Cost:** Free (runs on your hardware)
- **Setup:**
  ```json
  {
    "mode": "api",
    "provider": "ollama",
    "model": "llama3",
    "api_base": "http://localhost:11434"
  }
  ```

## Configuration File

Create `config.json` in the HomeSchool root directory:

```json
{
  "mode": "cli",
  "provider": "claude-code",
  "model": "claude-opus-4-6",
  "api_key": "",
  "api_base": "",
  "initial_lessons": 3
}
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `mode` | Yes | `cli` (subprocess) or `api` (HTTP calls) |
| `provider` | Yes | `claude-code`, `anthropic`, `openai`, or `ollama` |
| `model` | Yes | Model identifier (provider-specific) |
| `api_key` | For API mode | API key (not needed for Ollama or CLI mode) |
| `api_base` | For Ollama | Base URL for the API (default varies by provider) |
| `initial_lessons` | No | Number of lessons to generate on topic creation (default: 3) |

## Lesson Quality

Lesson quality depends on the model you choose. The system prompts are optimized for Claude Opus but work with any capable model. Recommended minimums:

- **Best quality:** Claude Opus, GPT-4o
- **Good quality:** Claude Sonnet, GPT-4o-mini
- **Varies:** Local models depend on size — 70B+ parameters recommended for well-structured HTML lessons
