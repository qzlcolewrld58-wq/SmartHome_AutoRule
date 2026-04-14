from __future__ import annotations

import os

from dotenv import load_dotenv

from deepseek_llm_client import DeepSeekLLMClient
from mock_llm_client import MockLLMClient


load_dotenv()


def _provider_from_env(env_name: str, default: str) -> str:
    return os.getenv(env_name, default).strip().lower()


def get_default_llm_client():
    provider = _provider_from_env("LLM_PROVIDER", "deepseek")
    if provider == "deepseek":
        return DeepSeekLLMClient()
    return MockLLMClient()


def get_experiment_llm_client():
    provider = _provider_from_env("EXPERIMENT_LLM_PROVIDER", "mock")
    if provider == "deepseek":
        return DeepSeekLLMClient()
    return MockLLMClient()
