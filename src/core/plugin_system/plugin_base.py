import abc
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

class BasePlugin(abc.ABC):
    """Base class that all Lumi plugins must inherit from"""
    
    def __init__(self, name: str, version: str = "1.0.0", description: str = ""):
        self.name = name
        self.version = version
        self.description = description
        self.logger = logging.getLogger(f"plugin.{name}")
        self.enabled = False
        self.config = {}
        self.data_path = None
        
    # Required methods that plugins must implement
    @abc.abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin - MUST BE IMPLEMENTED BY SUBCLASS"""
        pass
    
    @abc.abstractmethod
    async def unload(self) -> bool:
        """Cleanup and unload the plugin - MUST BE IMPLEMENTED BY SUBCLASS"""
        pass
    
    # Optional lifecycle methods that plugins can override
    async def on_load(self) -> None:
        """Called when plugin is loaded"""
        self.logger.info(f"Plugin {self.name} loaded")
    
    async def on_enable(self) -> None:
        """Called when plugin is enabled"""
        self.enabled = True
        self.logger.info(f"Plugin {self.name} enabled")
    
    async def on_disable(self) -> None:
        """Called when plugin is disabled"""
        self.enabled = False
        self.logger.info(f"Plugin {self.name} disabled")
    
    # Event handlers that plugins can override
    async def on_message_received(self, message: str, message_type: str = "user") -> Optional[str]:
        """Called when a message is received - can return modified message or None"""
        return None
    
    async def on_message_sent(self, message: str) -> None:
        """Called before a message is sent to user"""
        pass
    
    async def on_emotion_changed(self, emotion: str, intensity: float) -> None:
        """Called when AI emotion changes"""
        pass
    
    async def on_memory_stored(self, memory_type: str, content: str) -> None:
        """Called when new memory is stored"""
        pass
    
    async def on_voice_input(self, audio_data: Any) -> Optional[str]:
        """Called when voice input is received - can return processed text"""
        return None
    
    async def on_voice_output(self, text: str) -> Optional[str]:
        """Called before voice output - can return modified text"""
        return None
    
    async def on_dashboard_update(self) -> Optional[Dict]:
        """Called when dashboard updates - can return metrics to display"""
        return None
    
    # Utility methods available to all plugins
    def get_plugin_data_path(self) -> Path:
        """Get the data directory for this plugin"""
        if not self.data_path:
            from config import settings
            self.data_path = Path(settings.DATA_DIR) / "plugins" / self.name
            self.data_path.mkdir(parents=True, exist_ok=True)
        return self.data_path
    
    def save_plugin_data(self, data: Any, filename: str) -> bool:
        """Save plugin data to file"""
        try:
            import json
            file_path = self.get_plugin_data_path() / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"Error saving plugin data: {e}")
            return False
    
    def load_plugin_data(self, filename: str, default: Any = None) -> Any:
        """Load plugin data from file"""
        try:
            import json
            file_path = self.get_plugin_data_path() / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except Exception as e:
            self.logger.error(f"Error loading plugin data: {e}")
            return default
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback"""
        return self.config.get(key, default)