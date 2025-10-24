import logging
import asyncio
import websockets
import json
from config import settings

class OBSIntegration:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.websocket = None
        self.is_connected = False
        self.websocket_url = "ws://localhost:4455"  # Default OBS WebSocket port
        
    async def connect(self):
        """Connect to OBS WebSocket"""
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            self.is_connected = True
            self.logger.info("Connected to OBS WebSocket")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to OBS: {e}")
            return False
    
    async def set_chat_overlay(self, text, source_name="Lumi_Chat"):
        """Update OBS text source with chat messages"""
        if not self.is_connected:
            return False
            
        try:
            request = {
                "request-type": "SetTextGDIPlusProperties",
                "source": source_name,
                "text": text
            }
            
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            self.logger.info(f"Updated OBS chat overlay: {text[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating OBS overlay: {e}")
            return False
    
    async def trigger_scene_change(self, scene_name):
        """Change OBS scene"""
        if not self.is_connected:
            return False
            
        try:
            request = {
                "request-type": "SetCurrentScene",
                "scene-name": scene_name
            }
            
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            self.logger.info(f"Changed OBS scene to: {scene_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error changing OBS scene: {e}")
            return False
    
    async def start_stream(self):
        """Start OBS streaming"""
        if not self.is_connected:
            return False
            
        try:
            request = {"request-type": "StartStream"}
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            self.logger.info("Started OBS stream")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting OBS stream: {e}")
            return False
    
    async def stop_stream(self):
        """Stop OBS streaming"""
        if not self.is_connected:
            return False
            
        try:
            request = {"request-type": "StopStream"}
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            self.logger.info("Stopped OBS stream")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping OBS stream: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from OBS"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            self.logger.info("Disconnected from OBS")