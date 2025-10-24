import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"

# Ollama Settings
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "hf.co/mradermacher/L3.1-Dark-Reasoning-LewdPlay-evo-Hermes-R1-Uncensored-8B-i1-GGUF:Q6_K"

# VTube Studio Settings
VTS_WEBSOCKET_URL = "ws://localhost:8001"
VTS_TOKEN = os.getenv('VTS_TOKEN', '')  # Set in environment variables

# Audio Settings
AUDIO_SAMPLE_RATE = 22050
AUDIO_CHUNK_SIZE = 1024

# Memory Settings
VECTOR_MEMORY_PATH = DATA_DIR / "memory" / "vector_memory.db"
CONVERSATION_HISTORY_PATH = DATA_DIR / "memory" / "conversation_history.json"

# Web Interface Settings
WEB_HOST = "0.0.0.0"
WEB_PORT = 5000

# Discord Settings
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')  # Set in environment variables

# TTS/STT Settings
TTS_VOICE_MODEL = "en_US-lessac-medium.onnx"
STT_MODEL = "base"