# Learning Hub

A self-hosted, single-tenant AI learning system that generates structured multi-lesson courses from user-defined topics using configurable LLM providers (Claude CLI, API, or local models). The system uses a bootstrap configuration flow and serves generated content as static HTML accessible from any device.

## Quick Start (Docker)

```bash
git clone https://github.com/iamalexandar/learning-hub.git
cd learning-hub
docker compose up -d
```

Open http://localhost:8080 — the browser-based setup will guide you through provider configuration.

## Quick Start (Manual)

```bash
git clone https://github.com/iamalexandar/learning-hub.git
cd learning-hub
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python server.py
```

Open http://localhost:8080

## AI Providers

| Provider | Cost | Requirements |
|----------|------|--------------|
| Claude Code CLI | Included in Max/Pro subscription | Claude Code installed locally |
| Anthropic API | Pay per token | API key |
| OpenAI API | Pay per token | API key |
| Ollama | Free | Ollama running locally |

See [PROVIDERS.md](PROVIDERS.md) for detailed configuration.

## How It Works

1. Click **+** to create a new topic
2. Chat with AI about what you want to learn
3. Review and approve the proposed syllabus
4. Lessons are generated automatically
5. Access your lessons anytime on your home network

## Configuration

On first run, the browser-based setup page configures your `config.json`. You can also create it manually:

```json
{
  "mode": "cli",
  "provider": "claude-code",
  "model": "claude-opus-4-6",
  "api_key": "",
  "api_base": "",
  "initial_lessons": 3,
  "topics_dir": "./topics"
}
```

### Config fields

| Field | Values | Description |
|-------|--------|-------------|
| `mode` | `cli`, `api` | `cli` runs Claude Code CLI locally, `api` calls provider HTTP APIs |
| `provider` | `claude-code`, `anthropic`, `openai`, `ollama` | Which AI service to use |
| `model` | any model ID | e.g. `claude-opus-4-6`, `claude-sonnet-4-6`, `gpt-4o`, `llama3` |
| `api_key` | string | API key for Anthropic or OpenAI (not needed for CLI or Ollama) |
| `api_base` | URL | Custom API endpoint (only needed for Ollama, defaults to `http://localhost:11434`) |
| `initial_lessons` | number | How many lessons to generate when a new topic is created (default: `3`) |
| `topics_dir` | path | Where topics are stored (default: `./topics`) |

### Example configs

**Claude Code CLI** (requires local Claude Code installation + subscription):
```json
{ "mode": "cli", "provider": "claude-code", "model": "claude-opus-4-6" }
```

**Anthropic API** (requires API key):
```json
{ "mode": "api", "provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "sk-ant-..." }
```

**OpenAI API** (requires API key):
```json
{ "mode": "api", "provider": "openai", "model": "gpt-4o", "api_key": "sk-..." }
```

**Ollama** (free, local, no account needed):
```json
{ "mode": "api", "provider": "ollama", "model": "llama3", "api_base": "http://localhost:11434" }
```

## Docker with Ollama (Free, Local)

```bash
# Uncomment the ollama service in docker-compose.yml, then:
docker compose up -d
docker compose exec ollama ollama pull llama3
```

Configure the setup page with provider "Ollama" and model "llama3".

## Project Structure

```
├── server.py          # Flask application
├── config.json        # AI provider config (created on setup)
├── topics/            # Generated content (persisted)
├── templates/         # Jinja2 templates
├── static/            # CSS, JS
├── Dockerfile
└── docker-compose.yml
```
