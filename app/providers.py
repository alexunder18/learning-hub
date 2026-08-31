import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

import requests as http_requests

from .config import load_config

# Token usage from the most recent ai_complete() call, per thread — lesson
# generation runs one worker thread per topic plus a glossary thread, so a
# shared global would interleave.
_usage_state = threading.local()


def _record_usage(**fields):
    _usage_state.last = fields


def get_last_usage():
    """Usage of the last ai_complete() on this thread, or None if unavailable."""
    return getattr(_usage_state, "last", None)


def clear_usage():
    _usage_state.last = None


def ai_complete(prompt, timeout=300):
    cfg = load_config()
    if not cfg:
        raise RuntimeError("No config.json — run setup first")

    mode = cfg.get("mode", "cli")
    provider = cfg.get("provider", "claude-code")
    model = cfg.get("model", "claude-opus-4-6")

    if mode == "cli":
        return _cli_complete(prompt, model, timeout)
    elif provider == "anthropic":
        return _anthropic_complete(prompt, model, cfg["api_key"], timeout)
    elif provider in ("openai", "ollama"):
        base = cfg.get("api_base", "")
        if provider == "ollama" and not base:
            base = "http://localhost:11434"
        return _openai_complete(prompt, model, cfg.get("api_key", ""), base, timeout)
    else:
        raise RuntimeError(f"Unknown provider: {provider}")


def ai_chat(messages, system_prompt):
    cfg = load_config()
    mode = cfg.get("mode", "cli") if cfg else "cli"
    provider = cfg.get("provider", "claude-code") if cfg else "claude-code"

    if mode == "cli" or provider != "anthropic":
        prompt_parts = [f"System instructions:\n{system_prompt}\n\nConversation so far:"]
        for msg in messages:
            prompt_parts.append(f"\n{msg['role'].capitalize()}: {msg['content']}")
        prompt_parts.append("\nAssistant:")
        return ai_complete("\n".join(prompt_parts), timeout=180)

    return _anthropic_chat(messages, system_prompt, cfg)


def ai_generate(prompt, system_prompt):
    return ai_complete(f"System instructions:\n{system_prompt}\n\n{prompt}", timeout=600)


def _cli_complete(prompt, model, timeout):
    claude_cmd = shutil.which("claude") or "claude"
    env = os.environ.copy()
    env["HOME"] = str(Path.home())

    # --tools "" disables every built-in tool. Without it the CLI runs as a full
    # agent: it writes the lesson to a path of its own choosing and returns a prose
    # summary instead of the HTML, which then gets saved as the lesson.
    # --output-format json wraps the text in an envelope carrying token usage.
    result = subprocess.run(
        [claude_cmd, "-p", "-", "--model", model, "--tools", "", "--output-format", "json"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )

    if result.returncode != 0:
        err = result.stderr.strip() or f"claude exited with code {result.returncode}"
        print(f"[CLI ERROR] {err}")
        raise RuntimeError(err)

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        # Older CLI, or --output-format unsupported: fall back to raw stdout.
        _record_usage(provider="claude-code", model=model)
        return result.stdout.strip()

    if payload.get("is_error"):
        raise RuntimeError(payload.get("result") or "claude reported an error")

    usage = payload.get("usage") or {}
    _record_usage(
        provider="claude-code",
        model=model,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cache_read=usage.get("cache_read_input_tokens", 0),
        cache_creation=usage.get("cache_creation_input_tokens", 0),
        cost_usd=payload.get("total_cost_usd"),
        api_duration_ms=payload.get("duration_ms"),
        num_turns=payload.get("num_turns"),
        session_id=payload.get("session_id"),
        model_usage=payload.get("modelUsage") or {},
    )
    return (payload.get("result") or "").strip()


def _anthropic_complete(prompt, model, api_key, timeout):
    resp = http_requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 16000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Anthropic API error {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    _record_anthropic_usage(model, data)
    return data["content"][0]["text"]


def _record_anthropic_usage(model, data):
    usage = data.get("usage") or {}
    _record_usage(
        provider="anthropic",
        model=data.get("model", model),
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cache_read=usage.get("cache_read_input_tokens", 0),
        cache_creation=usage.get("cache_creation_input_tokens", 0),
    )


def _openai_complete(prompt, model, api_key, api_base, timeout):
    if not api_base:
        api_base = "https://api.openai.com/v1"

    if "11434" in api_base or "ollama" in api_base:
        url = f"{api_base.rstrip('/')}/api/chat"
        resp = http_requests.post(
            url,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=timeout,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama API error {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        _record_usage(
            provider="ollama",
            model=data.get("model", model),
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
        )
        return data["message"]["content"]

    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {"content-type": "application/json"}
    if api_key:
        headers["authorization"] = f"Bearer {api_key}"

    resp = http_requests.post(
        url,
        headers=headers,
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 16000,
        },
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI API error {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    usage = data.get("usage") or {}
    _record_usage(
        provider="openai",
        model=data.get("model", model),
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
    )
    return data["choices"][0]["message"]["content"]


def _anthropic_chat(messages, system_prompt, cfg):
    api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

    resp = http_requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": cfg.get("api_key", ""),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": cfg.get("model", "claude-sonnet-4-6"),
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": api_messages,
        },
        timeout=180,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Anthropic API error {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    _record_anthropic_usage(cfg.get("model", "claude-sonnet-4-6"), data)
    return data["content"][0]["text"]
