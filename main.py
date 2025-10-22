#!/usr/bin/env python3
"""
Lumi AI Companion - Main Entry Point
"""

import asyncio
import logging
import threading
import sys
import traceback
from src.utils.logger import setup_logging
from src.core.ai_engine import AIEngine
from src.integrations.ollama_client import OllamaClient
from src.core.memory_system import MemorySystem
from src.web.server import WebServer
from src.integrations.discord_bot import LumiDiscordBot
from src.integrations.speech_tts import TTSEngine
from src.integrations.speech_stt import STTEngine
from src.integrations.vtube_studio import VTubeStudio
from src.core.plugin_system.plugin_manager import PluginManager
from config import settings

class LumiCompanion:
    def __init__(self):
        self.logger = setup_logging()
        self.memory_system = None
        self.ai_engine = None
        self.ollama_client = None
        self.tts_engine = None
        self.stt_engine = None
        self.vts_client = None
        self.web_server = None
        self.discord_bot = None
        self.plugin_manager = None
        self.web_thread = None
        
    async def initialize(self):
        """Initialize all core systems"""
        print("Initializing Lumi AI Companion...")
        
        try:
            # Initialize core systems
            self.memory_system = MemorySystem()
            self.ollama_client = OllamaClient()
            
            # Initialize TTS/STT
            print("Initializing TTS/STT...")
            self.tts_engine = TTSEngine()
            self.stt_engine = STTEngine()
            
            # Initialize VTube Studio only if enabled
            if settings.get('vtube_studio.enabled', False):
                print("Initializing VTube Studio...")
                self.vts_client = VTubeStudio()
            else:
                print("VTube Studio disabled in settings")
                self.vts_client = None
            
            # Initialize AI Engine with all integrations
            self.ai_engine = AIEngine(
                self.ollama_client, 
                self.memory_system,
                self.tts_engine,
                self.stt_engine,
                self.vts_client
            )
            
            # Load character data
            print("Loading character data...")
            await self.ai_engine.load_character()
            
            # Initialize memory system
            print("Initializing memory system...")
            await self.memory_system.initialize()
            
            # Initialize Plugin System
            print("Initializing plugin system...")
            self.plugin_manager = PluginManager(self.ai_engine)
            plugin_success = await self.plugin_manager.initialize()
            if plugin_success:
                print(f"✓ Plugin system loaded with {len(self.plugin_manager.plugins)} plugins")
                # Connect plugin manager to AI engine
                self.ai_engine.plugin_manager = self.plugin_manager
            else:
                print("⚠ Plugin system initialization had issues, but continuing...")
            
            # Initialize WebUI with mobile and streaming support
            print("Initializing WebUI with mobile support...")
            self.web_server = WebServer(self.ai_engine, settings.WEB_HOST, settings.WEB_PORT)
            
            # Initialize Discord bot only if enabled
            if settings.get('discord.enabled', False):
                print("Initializing Discord bot...")
                self.discord_bot = LumiDiscordBot(self.ai_engine)
            else:
                print("Discord bot disabled in settings")
                self.discord_bot = None
            
            # Initialize TTS/STT engines
            await self.tts_engine.initialize()
            await self.stt_engine.initialize()
            
            # Connect to VTube Studio if enabled
            if self.vts_client:
                await self.vts_client.connect()
            
            print("Lumi AI Companion initialized successfully!")
            return True
            
        except Exception as e:
            print(f"Failed to initialize Lumi: {e}")
            traceback.print_exc()
            return False
    
    def start_web_server(self):
        """Start the web server in a separate thread"""
        try:
            self.web_server.run()
        except Exception as e:
            self.logger.error(f"Web server error: {e}")
    
    async def start_discord_bot(self):
        """Start the Discord bot"""
        if not self.discord_bot:
            return
            
        try:
            success = await self.discord_bot.start()
            if success:
                self.logger.info("Discord bot started successfully")
            else:
                self.logger.warning("Discord bot failed to start")
        except Exception as e:
            self.logger.error(f"Discord bot error: {e}")
    
    async def start(self):
        """Start the main companion loop"""
        print("Starting Lumi AI Companion...")
        
        if not await self.initialize():
            print("Failed to initialize Lumi. Exiting.")
            return
        
        try:
            # Start WebUI in separate thread
            self.web_thread = threading.Thread(target=self.start_web_server, daemon=True)
            self.web_thread.start()
            print("WebUI server thread started")
            
            # Start Discord bot if enabled
            discord_task = None
            if self.discord_bot:
                discord_task = asyncio.create_task(self.start_discord_bot())
                print("Discord bot task created")
            else:
                print("Discord bot disabled in settings")
            
            print("Lumi AI Companion is now running!")
            print(f"WebUI available at: http://{settings.WEB_HOST}:{settings.WEB_PORT}")
            print(f"Ollama Model: {settings.OLLAMA_MODEL}")
            
            if self.plugin_manager and self.plugin_manager.plugins:
                print(f"Plugins loaded: {', '.join(self.plugin_manager.plugins.keys())}")
            
            if self.vts_client:
                print("VTube Studio: Enabled")
            else:
                print("VTube Studio: Disabled")
                
            if self.discord_bot:
                print("Discord Bot: Enabled")
            else:
                print("Discord Bot: Disabled")
                
            print("Voice commands available: Say 'Hey Lumi' to activate voice input")
            print("Press Ctrl+C to stop")
            
            # Enhanced voice command loop with plugin support
            async def voice_command_loop():
                while True:
                    try:
                        # Check for voice input with plugin preprocessing
                        if (self.stt_engine and self.stt_engine.is_initialized and 
                            self.plugin_manager):
                            # This is where you'd integrate wake word detection
                            # and plugin voice processing
                            pass
                    except Exception as e:
                        self.logger.error(f"Voice loop error: {e}")
                    await asyncio.sleep(1)
            
            voice_task = asyncio.create_task(voice_command_loop())
            
            # Plugin monitoring task
            async def plugin_monitor_loop():
                while True:
                    try:
                        # Monitor plugin health and metrics
                        if self.plugin_manager:
                            enabled_plugins = [name for name, plugin in self.plugin_manager.plugins.items() 
                                            if plugin.enabled]
                            if enabled_plugins:
                                self.logger.debug(f"Active plugins: {enabled_plugins}")
                    except Exception as e:
                        self.logger.error(f"Plugin monitor error: {e}")
                    await asyncio.sleep(30)  # Check every 30 seconds
            
            monitor_task = asyncio.create_task(plugin_monitor_loop())
            
            # Keep the main thread alive
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\nReceived interrupt signal. Shutting down...")
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")
            traceback.print_exc()
        finally:
            # Graceful shutdown
            print("Initiating graceful shutdown...")
            
            if self.plugin_manager:
                print("Shutting down plugin system...")
                await self.plugin_manager.shutdown()
            
            if self.discord_bot:
                print("Stopping Discord bot...")
                await self.discord_bot.stop()
            
            if self.vts_client:
                print("Disconnecting from VTube Studio...")
                await self.vts_client.disconnect()
            
            print("Lumi AI Companion shutdown complete.")

def main():
    """Main entry point with error handling"""
    try:
        companion = LumiCompanion()
        asyncio.run(companion.start())
    except KeyboardInterrupt:
        print("\nLumi AI Companion stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        print("Check data/logs/lumi_companion.log for details")
        traceback.print_exc()
        input("Press Enter to close...")

if __name__ == "__main__":
    main()