import os
import json
from pathlib import Path

class Settings:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.config_path = self.base_dir / "config" / "settings.json"
        self._load_config()
    
    def _load_config(self):
        """Load configuration from JSON file"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default configuration file"""
        self._config = {
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "llama2",
                "temperature": 0.7,
                "max_tokens": 2048
            },
            "discord": {
                "token": os.getenv('DISCORD_TOKEN', ''),
                "command_prefix": "!",
                "enabled": False
            },
            "vtube_studio": {
                "websocket_url": "ws://localhost:8001",
                "token": os.getenv('VTS_TOKEN', ''),
                "enabled": False
            },
            "web_interface": {
                "host": "0.0.0.0",
                "port": 5000,
                "debug": False
            },
            "audio": {
                "sample_rate": 22050,
                "chunk_size": 1024,
                "tts_voice": "en_US-lessac-medium.onnx",
                "stt_model": "base"
            },
            "plugins": {
                "auto_load": True,
                "scan_interval": 30
            },
            "memory": {
                "vector_memory_path": "data/memory/vector_memory.db",
                "conversation_history_path": "data/memory/conversation_history.json"
            }
        }
        self.save_config()
    
    def save_config(self):
        """Save configuration to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
    
    def get(self, key, default=None):
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key, value):
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        self.save_config()
    
    # Property accessors for common settings
    @property
    def OLLAMA_BASE_URL(self):
        return self.get('ollama.base_url')
    
    @property
    def OLLAMA_MODEL(self):
        return self.get('ollama.model')
    
    @property
    def DISCORD_TOKEN(self):
        return self.get('discord.token')
    
    @property
    def DISCORD_ENABLED(self):
        return self.get('discord.enabled')
    
    @property
    def VTS_WEBSOCKET_URL(self):
        return self.get('vtube_studio.websocket_url')
    
    @property
    def VTS_TOKEN(self):
        return self.get('vtube_studio.token')
    
    @property
    def WEB_HOST(self):
        return self.get('web_interface.host')
    
    @property
    def WEB_PORT(self):
        return self.get('web_interface.port')
    
    @property
    def PLUGINS_DIR(self):
        return self.base_dir / "plugins"
    
    @property
    def DATA_DIR(self):
        return self.base_dir / "data"
    
    @property
    def CONFIG_DIR(self):
        return self.base_dir / "config"
    
    # Memory system properties
    @property
    def VECTOR_MEMORY_PATH(self):
        memory_path = self.get('memory.vector_memory_path', 'data/memory/vector_memory.db')
        return self.base_dir / memory_path
    
    @property
    def CONVERSATION_HISTORY_PATH(self):
        history_path = self.get('memory.conversation_history_path', 'data/memory/conversation_history.json')
        return self.base_dir / history_path
    
    # Audio properties
    @property
    def AUDIO_SAMPLE_RATE(self):
        return self.get('audio.sample_rate', 22050)
    
    @property
    def AUDIO_CHUNK_SIZE(self):
        return self.get('audio.chunk_size', 1024)
    
    @property
    def TTS_VOICE_MODEL(self):
        return self.get('audio.tts_voice', 'en_US-lessac-medium.onnx')
    
    @property
    def STT_MODEL(self):
        return self.get('audio.stt_model', 'base')

# Global settings instance
settings = Settings()