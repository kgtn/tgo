from typing import Optional, List, Dict, Any
from app.config import settings
from app.core.logging import logger
from app.integrations.ai_client import AIClient

class LLMProvider:
    @staticmethod
    async def chat_completion(
        provider_id: str,
        model: str,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        project_id: Optional[str] = None
    ) -> str:
        logger.info(f"LLM Chat Completion via AI Service: provider_id={provider_id} model={model}")
        
        # Use a default project_id if not provided
        active_project_id = project_id or "00000000-0000-0000-0000-000000000000"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        
        payload = {
            "provider_id": provider_id,
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            data = await AIClient.chat_completions(active_project_id, payload)
            # OpenAI compatible response format: choices[0].message.content
            return data["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"LLM Chat Completion failed: {e}")
            raise

