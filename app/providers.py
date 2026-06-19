import os
import shutil
import subprocess
from pathlib import Path

import requests as http_requests

from .config import load_config


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

    result = subprocess.run(
        [claude_cmd, "-p", "-", "--model", model],
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

    return result.stdout.strip()


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
    return resp.json()["content"][0]["text"]


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
        return resp.json()["message"]["content"]

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
    return resp.json()["choices"][0]["message"]["content"]


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
    return resp.json()["content"][0]["text"]
