"""llm.py — LLMProvider interface + Groq and Ollama providers (§5.10).

Providers return a list of raw suggestion dicts (unvalidated) or raise on any error.
"""
from __future__ import annotations

import json
import os

import httpx

from app import config


class LLMProvider:
    model: str | None = None
    last_usage: dict | None = None   # token counts from the last call, for scripts/eval_advisor.py

    def suggest(self, system_prompt: str, user_message: str) -> list[dict]:
        raise NotImplementedError

    def suggest_one(self, system_prompt: str, user_message: str) -> dict:
        """One JSON object rather than a list of suggestions (the assistant's shape)."""
        raise NotImplementedError


def _parse_object(text: str) -> dict:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("not a JSON object")
    return data


def _parse(text: str) -> list[dict]:
    data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get("suggestions"), list):
        raise ValueError("no suggestions list")
    return data["suggestions"]


class GroqProvider(LLMProvider):
    def __init__(self) -> None:
        self.model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        self._key = os.environ["GROQ_API_KEY"]

    def _chat(self, system_prompt: str, user_message: str) -> str:
        body = {"model": self.model, "temperature": 0.2, "max_tokens": 4000,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system_prompt},
                             {"role": "user", "content": user_message}]}
        if self.model.startswith("openai/gpt-oss"):
            # reasoning model: its thinking counts against max_tokens, keep it short
            body["reasoning_effort"] = "low"
        for attempt in range(2):
            r = httpx.post("https://api.groq.com/openai/v1/chat/completions",
                           headers={"Authorization": f"Bearer {self._key}"},
                           json=body, timeout=config.LLM_TIMEOUT_S)
            # Groq answers 400 json_validate_failed when the model produced invalid JSON;
            # that is random, so one retry usually succeeds
            if r.status_code == 400 and "json_validate_failed" in r.text and attempt == 0:
                continue
            r.raise_for_status()
            payload = r.json()
            self.last_usage = payload.get("usage")
            return payload["choices"][0]["message"]["content"]
        raise RuntimeError("unreachable")

    def suggest(self, system_prompt: str, user_message: str) -> list[dict]:
        return _parse(self._chat(system_prompt, user_message))

    def suggest_one(self, system_prompt: str, user_message: str) -> dict:
        return _parse_object(self._chat(system_prompt, user_message))


class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        self.model = os.environ.get("OLLAMA_MODEL", "llama3.1")
        self._url = os.environ["OLLAMA_URL"].rstrip("/")

    def _chat(self, system_prompt: str, user_message: str) -> str:
        r = httpx.post(
            f"{self._url}/api/chat",
            json={"model": self.model, "stream": False, "format": "json",
                  "messages": [{"role": "system", "content": system_prompt},
                               {"role": "user", "content": user_message}]},
            timeout=config.LLM_TIMEOUT_S,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]

    def suggest(self, system_prompt: str, user_message: str) -> list[dict]:
        return _parse(self._chat(system_prompt, user_message))

    def suggest_one(self, system_prompt: str, user_message: str) -> dict:
        return _parse_object(self._chat(system_prompt, user_message))
