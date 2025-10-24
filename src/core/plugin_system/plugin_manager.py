import importlib
import inspect
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
from .plugin_base import BasePlugin
from .plugin_registry import PluginRegistry
from .events import PluginEvents

class PluginManager:
    """Manages loading, unloading, and communication between plugins"""
    
    def __init__(self, ai_engine=None):
        self.ai_engine = ai_engine
        self.logger = logging.getLogger(__name__)
        self.registry = PluginRegistry()
        self.events = PluginEvents()
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_paths = []
        
        # Set up default plugin paths
        self._setup_plugin_paths()
    
    def _setup_plugin_paths(self):
        """Set up default plugin search paths"""
        base_dir = Path(__file__).parent.parent.parent.parent
        self.plugin_paths = [
            base_dir / "plugins" / "core",      # Built-in plugins
            base_dir / "plugins" / "community", # User plugins
        ]
        self.logger.info(f"🔧 Plugin paths configured: {[str(p) for p in self.plugin_paths]}")
    
    async def initialize(self) -> bool:
        """Initialize the plugin manager and load all plugins"""
        try:
            self.logger.info("🚀 Initializing plugin manager...")
            
            # Load plugin configuration
            await self.registry.load_config()
            
            # Discover and load plugins
            await self._discover_plugins()
            
            # Initialize loaded plugins
            await self._initialize_plugins()
            
            self.logger.info(f"✅ Plugin manager initialized with {len(self.plugins)} plugins: {list(self.plugins.keys())}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize plugin manager: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    async def _discover_plugins(self) -> None:
        """Discover available plugins in plugin paths"""
        self.logger.info(f"🔍 Searching for plugins in: {[str(p) for p in self.plugin_paths]}")
        
        for plugin_path in self.plugin_paths:
            if not plugin_path.exists():
                self.logger.warning(f"❌ Plugin path does not exist: {plugin_path}")
                continue
                
            self.logger.info(f"📁 Scanning directory: {plugin_path}")
            
            try:
                # List all items in the directory
                items = list(plugin_path.iterdir())
                self.logger.info(f"📋 Found {len(items)} items in {plugin_path.name}: {[item.name for item in items]}")
                
                for plugin_dir in items:
                    if plugin_dir.is_dir() and not plugin_dir.name.startswith('_'):
                        self.logger.info(f"🎯 Found potential plugin directory: {plugin_dir.name}")
                        await self._load_plugin_from_directory(plugin_dir)
                    else:
                        self.logger.debug(f"⏭️ Skipping: {plugin_dir.name} (not a valid plugin directory)")
            except Exception as e:
                self.logger.error(f"❌ Error scanning {plugin_path}: {e}")
    
    async def _load_plugin_from_directory(self, plugin_dir: Path) -> bool:
        """Load a plugin from a directory"""
        plugin_name = plugin_dir.name
        self.logger.info(f"📦 Attempting to load plugin: {plugin_name} from {plugin_dir}")
        
        try:
            # Determine the module path based on parent directory
            if plugin_dir.parent.name == "core":
                module_path = f"plugins.core.{plugin_name}"
            elif plugin_dir.parent.name == "community":
                module_path = f"plugins.community.{plugin_name}"
            else:
                module_path = f"plugins.{plugin_name}"
                
            self.logger.info(f"🔗 Module path: {module_path}")

            # Check if plugin is enabled in config
            if not self.registry.is_plugin_enabled(plugin_name):
                self.logger.info(f"⚙️ Plugin {plugin_name} is disabled in config, skipping")
                return False

            # Check for __init__.py
            init_file = plugin_dir / "__init__.py"
            if not init_file.exists():
                self.logger.warning(f"❌ No __init__.py found in {plugin_dir}")
                return False

            # Import the plugin module using importlib
            spec = importlib.util.spec_from_file_location(
                module_path, 
                init_file
            )
            if spec is None:
                self.logger.warning(f"❌ Could not create spec for {module_path}")
                return False
                
            module = importlib.util.module_from_spec(spec)
            
            # Add the module to sys.modules so it can be imported
            sys.modules[module_path] = module
            
            try:
                spec.loader.exec_module(module)
                self.logger.info(f"✅ Successfully imported module: {module_path}")
            except Exception as e:
                self.logger.error(f"❌ Error executing module {module_path}: {e}")
                return False

            # Find the plugin class (should be the only subclass of BasePlugin)
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BasePlugin) and 
                    obj != BasePlugin):
                    plugin_class = obj
                    self.logger.info(f"🎯 Found plugin class: {name}")
                    break
            
            if not plugin_class:
                self.logger.warning(f"❌ No plugin class found in {plugin_dir}")
                return False
            
            # Create plugin instance
            plugin_instance = plugin_class()
            plugin_instance.config = self.registry.get_plugin_config(plugin_name)
            
            self.plugins[plugin_name] = plugin_instance
            self.registry.register_plugin(plugin_name, plugin_instance)
            
            self.logger.info(f"✅ Successfully loaded plugin: {plugin_name} v{plugin_instance.version}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error loading plugin from {plugin_dir}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    async def _initialize_plugins(self) -> None:
        """Initialize all loaded plugins"""
        # Create a list of plugin names to avoid modifying the dictionary during iteration
        plugin_names = list(self.plugins.keys())
        
        for plugin_name in plugin_names:
            # Check if plugin still exists (might have been removed by previous iterations)
            if plugin_name not in self.plugins:
                continue
                
            plugin = self.plugins[plugin_name]
            try:
                self.logger.info(f"⚡ Initializing plugin: {plugin_name}")
                success = await plugin.initialize()
                if success:
                    await plugin.on_load()
                    if self.registry.is_plugin_enabled(plugin_name):
                        await plugin.on_enable()
                        self.logger.info(f"✅ Initialized and enabled plugin: {plugin_name}")
                    else:
                        self.logger.info(f"✅ Initialized plugin: {plugin_name} (disabled)")
                else:
                    self.logger.error(f"❌ Failed to initialize plugin: {plugin_name}")
                    # Remove from plugins dictionary
                    if plugin_name in self.plugins:
                        del self.plugins[plugin_name]
            except Exception as e:
                self.logger.error(f"❌ Error initializing plugin {plugin_name}: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                # Remove from plugins dictionary
                if plugin_name in self.plugins:
                    del self.plugins[plugin_name]
    
    # Event dispatching methods
    async def dispatch_message_received(self, message: str, message_type: str = "user") -> str:
        """Dispatch message_received event to all plugins"""
        processed_message = message
        
        for plugin_name, plugin in self.plugins.items():
            if plugin.enabled:
                try:
                    result = await plugin.on_message_received(processed_message, message_type)
                    if result is not None:
                        processed_message = result
                except Exception as e:
                    self.logger.error(f"Plugin {plugin_name} error in on_message_received: {e}")
        
        return processed_message
    
    async def dispatch_message_sent(self, message: str) -> None:
        """Dispatch message_sent event to all plugins"""
        for plugin_name, plugin in self.plugins.items():
            if plugin.enabled:
                try:
                    await plugin.on_message_sent(message)
                except Exception as e:
                    self.logger.error(f"Plugin {plugin_name} error in on_message_sent: {e}")
    
    async def dispatch_emotion_changed(self, emotion: str, intensity: float) -> None:
        """Dispatch emotion_changed event to all plugins"""
        for plugin_name, plugin in self.plugins.items():
            if plugin.enabled:
                try:
                    await plugin.on_emotion_changed(emotion, intensity)
                except Exception as e:
                    self.logger.error(f"Plugin {plugin_name} error in on_emotion_changed: {e}")
    
    async def dispatch_dashboard_update(self) -> List[Dict]:
        """Dispatch dashboard_update event to all plugins and collect metrics"""
        metrics = []
        for plugin_name, plugin in self.plugins.items():
            if plugin.enabled:
                try:
                    plugin_metrics = await plugin.on_dashboard_update()
                    if plugin_metrics:
                        plugin_metrics['plugin'] = plugin_name
                        metrics.append(plugin_metrics)
                except Exception as e:
                    self.logger.error(f"Plugin {plugin_name} error in on_dashboard_update: {e}")
        return metrics
    
    async def dispatch_memory_stored(self, memory_type: str, content: str) -> None:
        """Dispatch memory_stored event to all plugins"""
        for plugin_name, plugin in self.plugins.items():
            if plugin.enabled:
                try:
                    await plugin.on_memory_stored(memory_type, content)
                except Exception as e:
                    self.logger.error(f"Plugin {plugin_name} error in on_memory_stored: {e}")
    
    async def dispatch_voice_input(self, audio_data: Any) -> List[Any]:
        """Dispatch voice_input event to all plugins and collect results"""
        results = []
        for plugin_name, plugin in self.plugins.items():
            if plugin.enabled:
                try:
                    result = await plugin.on_voice_input(audio_data)
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Plugin {plugin_name} error in on_voice_input: {e}")
        return results
    
    async def dispatch_voice_output(self, text: str) -> List[Any]:
        """Dispatch voice_output event to all plugins and collect results"""
        results = []
        for plugin_name, plugin in self.plugins.items():
            if plugin.enabled:
                try:
                    result = await plugin.on_voice_output(text)
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Plugin {plugin_name} error in on_voice_output: {e}")
        return results
    
    # Plugin management methods
    async def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a specific plugin"""
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            if not plugin.enabled:
                await plugin.on_enable()
                self.registry.enable_plugin(plugin_name)
                self.logger.info(f"✅ Enabled plugin: {plugin_name}")
                return True
        self.logger.warning(f"❌ Cannot enable plugin: {plugin_name} not found")
        return False
    
    async def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a specific plugin"""
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            if plugin.enabled:
                await plugin.on_disable()
                self.registry.disable_plugin(plugin_name)
                self.logger.info(f"✅ Disabled plugin: {plugin_name}")
                return True
        self.logger.warning(f"❌ Cannot disable plugin: {plugin_name} not found")
        return False
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a specific plugin"""
        self.logger.warning(f"🔄 Plugin reload not yet implemented for {plugin_name}")
        return False
    
    def get_plugin_info(self) -> List[Dict]:
        """Get information about all plugins"""
        info = []
        for name, plugin in self.plugins.items():
            info.append({
                'name': name,
                'version': plugin.version,
                'description': plugin.description,
                'enabled': plugin.enabled,
                'config': plugin.config
            })
        return info
    
    async def shutdown(self) -> None:
        """Shutdown all plugins and cleanup"""
        self.logger.info("🛑 Shutting down plugin manager...")
        for plugin_name, plugin in self.plugins.items():
            try:
                await plugin.unload()
                self.logger.info(f"✅ Unloaded plugin: {plugin_name}")
            except Exception as e:
                self.logger.error(f"❌ Error unloading plugin {plugin_name}: {e}")
        
        self.plugins.clear()
        self.logger.info("✅ Plugin manager shutdown complete")