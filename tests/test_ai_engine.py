import pytest
import asyncio
from src.core.ai_engine import AIEngine
from src.integrations.ollama_client import OllamaClient
from src.core.memory_system import MemorySystem

class TestAIEngine:
    @pytest.fixture
    async def ai_engine(self):
        ollama_client = OllamaClient()
        memory_system = MemorySystem()
        engine = AIEngine(ollama_client, memory_system)
        await engine.load_character()
        return engine
    
    @pytest.mark.asyncio
    async def test_character_loading(self, ai_engine):
        assert ai_engine.character_data is not None
        assert ai_engine.character_data['name'] == 'Lumi'
    
    @pytest.mark.asyncio 
    async def test_system_prompt_generation(self, ai_engine):
        prompt = ai_engine._build_system_prompt()
        assert "Lumi" in prompt
        assert "curious" in prompt
        assert "empathetic" in prompt