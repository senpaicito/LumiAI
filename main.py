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
            
            # Initialize VTube Studio
            print("Initializing VTube Studio...")
            self.vts_client = VTubeStudio()
            
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
            
            # Initialize WebUI with mobile and streaming support
            print("Initializing WebUI with mobile support...")
            self.web_server = WebServer(self.ai_engine, settings.WEB_HOST, settings.WEB_PORT)
            
            # Initialize Discord bot (optional)
            self.discord_bot = LumiDiscordBot(self.ai_engine)
            
            # Initialize TTS/STT engines
            await self.tts_engine.initialize()
            await self.stt_engine.initialize()
            
            # Connect to VTube Studio
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
        try:
            await self.discord_bot.start()
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
            
            # Start Discord bot if token is available
            discord_task = None
            if settings.DISCORD_TOKEN:
                discord_task = asyncio.create_task(self.start_discord_bot())
                print("Discord bot task created")
            else:
                print("No Discord token found. Discord bot disabled.")
            
            print("Lumi AI Companion is now running!")
            print(f"WebUI available at: http://{settings.WEB_HOST}:{settings.WEB_PORT}")
            print("Voice commands available: Say 'Hey Lumi' to activate voice input")
            print("Press Ctrl+C to stop")
            
            # Voice command loop
            async def voice_command_loop():
                while True:
                    # Simple voice activation (you can enhance this with wake word detection)
                    await asyncio.sleep(1)
            
            voice_task = asyncio.create_task(voice_command_loop())
            
            # Keep the main thread alive
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\nReceived interrupt signal. Shutting down...")
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")
            traceback.print_exc()
        finally:
            if self.discord_bot:
                await self.discord_bot.stop()
            if self.vts_client:
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
