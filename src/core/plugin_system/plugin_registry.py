import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from config.settings_manager import settings

class PluginRegistry:
    """Manages plugin configuration, state, and registration"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_path = Path(settings.CONFIG_DIR) / "plugin_config.json"
        self.plugin_configs: Dict[str, Any] = {}
        self.enabled_plugins: List[str] = []
        self.plugin_instances: Dict[str, Any] = {}
        
    async def load_config(self) -> bool:
        """Load plugin configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self.plugin_configs = config_data.get('plugins', {})
                    self.enabled_plugins = config_data.get('enabled_plugins', [])
                self.logger.info(f"✅ Loaded plugin config: {len(self.plugin_configs)} plugins configured")
            else:
                # Create default config
                await self._create_default_config()
            return True
        except Exception as e:
            self.logger.error(f"❌ Error loading plugin config: {e}")
            await self._create_default_config()
            return False
    
    async def _create_default_config(self) -> None:
        """Create default plugin configuration"""
        self.plugin_configs = {
            "example": {
                "enabled": False,
                "settings": {}
            }
        }
        self.enabled_plugins = []
        await self.save_config()
        self.logger.info("✅ Created default plugin configuration")
    
    async def save_config(self) -> bool:
        """Save plugin configuration to file"""
        try:
            config_data = {
                'plugins': self.plugin_configs,
                'enabled_plugins': self.enabled_plugins
            }
            
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✅ Saved plugin config to {self.config_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error saving plugin config: {e}")
            return False
    
    def register_plugin(self, plugin_name: str, plugin_instance: Any) -> None:
        """Register a plugin instance"""
        self.plugin_instances[plugin_name] = plugin_instance
        
        # Ensure plugin has a config entry - auto-enable new plugins
        if plugin_name not in self.plugin_configs:
            self.plugin_configs[plugin_name] = {
                "enabled": True,  # Auto-enable new plugins
                "settings": {}
            }
            # Also add to enabled plugins list
            if plugin_name not in self.enabled_plugins:
                self.enabled_plugins.append(plugin_name)
            self.logger.info(f"✅ Auto-enabled new plugin: {plugin_name}")
        else:
            self.logger.info(f"📝 Registered existing plugin: {plugin_name}")
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for a specific plugin"""
        return self.plugin_configs.get(plugin_name, {"enabled": False, "settings": {}})
    
    def update_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> bool:
        """Update configuration for a specific plugin"""
        if plugin_name in self.plugin_configs:
            self.plugin_configs[plugin_name].update(config)
            self.logger.info(f"✅ Updated config for plugin: {plugin_name}")
            return True
        self.logger.warning(f"❌ Cannot update config: plugin {plugin_name} not found")
        return False
    
    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled"""
        return plugin_name in self.enabled_plugins
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin"""
        if plugin_name in self.plugin_configs and plugin_name not in self.enabled_plugins:
            self.enabled_plugins.append(plugin_name)
            self.plugin_configs[plugin_name]['enabled'] = True
            self.logger.info(f"✅ Enabled plugin: {plugin_name}")
            return True
        self.logger.warning(f"❌ Cannot enable plugin: {plugin_name} not found or already enabled")
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin"""
        if plugin_name in self.enabled_plugins:
            self.enabled_plugins.remove(plugin_name)
            if plugin_name in self.plugin_configs:
                self.plugin_configs[plugin_name]['enabled'] = False
            self.logger.info(f"✅ Disabled plugin: {plugin_name}")
            return True
        self.logger.warning(f"❌ Cannot disable plugin: {plugin_name} not found or already disabled")
        return False
    
    def get_enabled_plugins(self) -> List[str]:
        """Get list of enabled plugins"""
        return self.enabled_plugins.copy()
    
    def get_all_plugins(self) -> List[str]:
        """Get list of all registered plugins"""
        return list(self.plugin_configs.keys())
    
    def get_plugin_instance(self, plugin_name: str) -> Any:
        """Get plugin instance by name"""
        return self.plugin_instances.get(plugin_name)