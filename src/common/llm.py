from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import httpx
from nonebot.log import logger

class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """
        Send a chat request to the LLM.
        messages: [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
        """
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(f"{self.base_url}/chat/completions", json=data, headers=headers)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"LLM API Error: {e}")
                return f"Error: {str(e)}"

class LLMService:
    _instance = None
    _provider: Optional[LLMProvider] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMService, cls).__new__(cls)
        return cls._instance

    def set_provider(self, provider: LLMProvider):
        self._provider = provider

    async def chat(self, prompt: str, history: List[Dict[str, str]] = None) -> str:
        if not self._provider:
            return "LLM Provider not configured."
        
        messages = history or []
        messages.append({"role": "user", "content": prompt})
        
        return await self._provider.chat(messages)

# Global Instance
llm_service = LLMService()

# Example usage (to be configured in bot.py or config):
# llm_service.set_provider(OpenAIProvider(api_key="sk-...", base_url="..."))
