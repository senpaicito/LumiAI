import json
import logging
import asyncio
import websockets
from config import settings

class VTubeStudio:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.websocket = None
        self.is_connected = False
        self.token = settings.VTS_TOKEN
        self.websocket_url = settings.VTS_WEBSOCKET_URL
        
        # Expression and hotkey tracking
        self.available_expressions = []
        self.available_hotkeys = []
        
    async def connect(self):
        """Connect to VTube Studio WebSocket"""
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            self.is_connected = True
            self.logger.info("Connected to VTube Studio")
            
            # Always attempt authentication
            authenticated = await self.authenticate()
            if authenticated:
                # Load available expressions and hotkeys
                await self.load_expressions()
                await self.load_hotkeys()
                return True
            else:
                self.logger.error("VTube Studio authentication failed")
                await self.disconnect()
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to connect to VTube Studio: {e}")
            return False
    
    async def authenticate(self):
        """Authenticate with VTube Studio"""
        if not self.is_connected:
            return False
            
        try:
            # If we have a token, try to use it
            if self.token:
                auth_request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "AuthRequest1",
                    "messageType": "AuthenticationRequest",
                    "data": {
                        "pluginName": "Lumi AI Companion",
                        "pluginDeveloper": "Lumi AI",
                        "authenticationToken": self.token
                    }
                }
                
                await self.websocket.send(json.dumps(auth_request))
                response = await self.websocket.recv()
                response_data = json.loads(response)
                
                if response_data.get("data", {}).get("authenticated"):
                    self.logger.info("VTube Studio authentication successful")
                    return True
                else:
                    self.logger.warning("Stored token invalid, requesting new token")
                    # Token is invalid, clear it and request new one
                    self.token = None
            
            # If no token or token invalid, request new authentication
            return await self.request_new_token()
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    async def request_new_token(self):
        """Request a new authentication token from VTube Studio"""
        try:
            # First request authentication token
            auth_token_request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "TokenRequest1",
                "messageType": "AuthenticationTokenRequest",
                "data": {
                    "pluginName": "Lumi AI Companion",
                    "pluginDeveloper": "Lumi AI"
                }
            }
            
            await self.websocket.send(json.dumps(auth_token_request))
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if response_data.get("data", {}).get("authenticationToken"):
                self.token = response_data["data"]["authenticationToken"]
                self.logger.info("New authentication token received")
                self.logger.info(f"Please approve the plugin in VTube Studio and save this token: {self.token}")
                
                # Wait a bit for user to approve, then try to authenticate
                await asyncio.sleep(5)
                return await self.authenticate_with_new_token()
            else:
                self.logger.error("Failed to get authentication token")
                return False
                
        except Exception as e:
            self.logger.error(f"Token request error: {e}")
            return False
    
    async def authenticate_with_new_token(self):
        """Authenticate using the newly acquired token"""
        try:
            auth_request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "AuthRequest2",
                "messageType": "AuthenticationRequest",
                "data": {
                    "pluginName": "Lumi AI Companion",
                    "pluginDeveloper": "Lumi AI",
                    "authenticationToken": self.token
                }
            }
            
            await self.websocket.send(json.dumps(auth_request))
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if response_data.get("data", {}).get("authenticated"):
                self.logger.info("Authentication with new token successful")
                # Here you might want to save the token to your config
                # await self.save_token_to_config()
                return True
            else:
                self.logger.error("Authentication with new token failed")
                return False
                
        except Exception as e:
            self.logger.error(f"New token authentication error: {e}")
            return False
    
    async def load_expressions(self):
        """Load available expressions from VTube Studio"""
        try:
            request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "GetExpressions1",
                "messageType": "ExpressionStateRequest"
            }
            
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if "data" in response_data and "expressions" in response_data["data"]:
                self.available_expressions = response_data["data"]["expressions"]
                self.logger.info(f"Loaded {len(self.available_expressions)} expressions")
                
        except Exception as e:
            self.logger.error(f"Error loading expressions: {e}")
    
    async def load_hotkeys(self):
        """Load available hotkeys from VTube Studio"""
        try:
            request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "GetHotkeys1",
                "messageType": "HotkeysInCurrentModelRequest"
            }
            
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if "data" in response_data and "availableHotkeys" in response_data["data"]:
                self.available_hotkeys = response_data["data"]["availableHotkeys"]
                self.logger.info(f"Loaded {len(self.available_hotkeys)} hotkeys")
                
        except Exception as e:
            self.logger.error(f"Error loading hotkeys: {e}")
    
    async def trigger_expression(self, expression_name):
        """Trigger a Live2D expression"""
        if not self.is_connected:
            return False
            
        try:
            # First try to find the expression by name
            expression_id = None
            for expr in self.available_expressions:
                if expression_name.lower() in expr.get("name", "").lower():
                    expression_id = expr.get("file")
                    break
            
            if expression_id:
                request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": f"Expression_{expression_name}",
                    "messageType": "ExpressionActivationRequest",
                    "data": {
                        "expressionFile": expression_id,
                        "active": True
                    }
                }
            else:
                # Fallback to hotkey if expression not found
                return await self.trigger_hotkey_by_name(expression_name)
            
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            self.logger.info(f"Triggered expression: {expression_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Expression trigger error: {e}")
            return False
    
    async def trigger_hotkey_by_name(self, hotkey_name):
        """Trigger a hotkey by name"""
        if not self.is_connected:
            return False
            
        try:
            hotkey_id = None
            for hotkey in self.available_hotkeys:
                if hotkey_name.lower() in hotkey.get("name", "").lower():
                    hotkey_id = hotkey.get("hotkeyID")
                    break
            
            if hotkey_id:
                return await self.trigger_hotkey(hotkey_id)
            else:
                self.logger.warning(f"Hotkey not found: {hotkey_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Hotkey trigger error: {e}")
            return False
    
    async def trigger_hotkey(self, hotkey_id):
        """Trigger a VTube Studio hotkey"""
        if not self.is_connected:
            return False
            
        try:
            request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": f"Hotkey_{hotkey_id}",
                "messageType": "HotkeyTriggerRequest",
                "data": {
                    "hotkeyID": hotkey_id
                }
            }
            
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            self.logger.info(f"Triggered hotkey: {hotkey_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Hotkey trigger error: {e}")
            return False
    
    async def send_emotional_state(self, emotion, intensity=0.5):
        """Send emotional state to VTube Studio"""
        # Map emotions to expressions/hotkeys
        emotion_mapping = {
            "happy": "smile",
            "sad": "sad",
            "angry": "angry",
            "surprised": "surprise",
            "thinking": "think",
            "confused": "confused",
            "excited": "excited"
        }
        
        expression = emotion_mapping.get(emotion, "idle")
        return await self.trigger_expression(expression)
    
    async def get_current_model(self):
        """Get current Live2D model information"""
        if not self.is_connected:
            return None
            
        try:
            request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "GetCurrentModel",
                "messageType": "CurrentModelRequest"
            }
            
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            return response_data.get("data", {})
            
        except Exception as e:
            self.logger.error(f"Error getting current model: {e}")
            return None
    
    async def disconnect(self):
        """Disconnect from VTube Studio"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            self.logger.info("Disconnected from VTube Studio")