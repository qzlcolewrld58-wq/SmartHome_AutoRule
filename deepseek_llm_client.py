from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


class DeepSeekLLMClient:
    """OpenAI-compatible DeepSeek client used for DSL generation."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> None:
        resolved_api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not resolved_api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured.")

        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")).strip()
        self.model = (model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")).strip()
        self.temperature = temperature
        self.client = OpenAI(api_key=resolved_api_key, base_url=self.base_url)
        self.last_trace: dict[str, Any] = {}

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {
                    "role": "system",
                    "content": "You convert Chinese smart-home instructions into strict JSON DSL. Output JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        text = response.choices[0].message.content or ""
        self.last_trace = {
            "provider": "deepseek",
            "base_url": self.base_url,
            "model": self.model,
            "finish_reason": response.choices[0].finish_reason,
            "usage": response.usage.model_dump() if response.usage else {},
        }
        return text
