import aiohttp
import logging
from config import settings

class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.temperature = getattr(settings, 'OLLAMA_TEMPERATURE', getattr(settings, 'ollama.temperature', 0.7))
        self.max_tokens = getattr(settings, 'OLLAMA_MAX_TOKENS', getattr(settings, 'ollama.max_tokens', 2048))
        self.logger = logging.getLogger(__name__)
    
    async def generate_response(self, user_input, system_prompt=None, context=None):
        """Generate response using Ollama API"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": user_input,
                    "system": system_prompt,
                    "stream": False,
                    "context": context or [],
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    }
                }
                
                # Remove None values from payload to avoid API issues
                if system_prompt is None:
                    payload.pop('system', None)
                
                async with session.post(
                    f"{self.base_url}/api/generate", 
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('response', '').strip()
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Ollama API error: {error_text}")
                        return "I'm having trouble responding right now."
                        
        except Exception as e:
            self.logger.error(f"Error calling Ollama: {e}")
            return "I'm having trouble connecting to my thoughts."
    
    async def check_connection(self):
        """Check if Ollama is running and accessible"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    return response.status == 200
        except:
            return False