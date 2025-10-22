import asyncio
import logging
import base64
import json
import threading
import time
from io import BytesIO
from flask_socketio import SocketIO, emit
from PIL import Image, ImageDraw, ImageFont

class Live2DStreamer:
    def __init__(self, socketio, vts_client=None):
        self.socketio = socketio
        self.vts_client = vts_client
        self.logger = logging.getLogger(__name__)
        self.is_streaming = False
        self.stream_thread = None
        self.current_emotion = "neutral"
        self.connected_clients = 0
        self.frame_buffer = None
        
        # VTube Studio API integration
        self.vts_api_connected = False
        self.hotkey_manager = None
        
        # Emotion to expression mapping for VTS
        self.emotion_expressions = {
            "happy": "smile",
            "sad": "sad", 
            "angry": "angry",
            "surprised": "surprise",
            "curious": "think",
            "confused": "confused",
            "excited": "excited",
            "thoughtful": "think",
            "neutral": "idle"
        }
        
        self.setup_socket_handlers()
    
    def setup_socket_handlers(self):
        """Setup WebSocket handlers for Live2D streaming"""
        @self.socketio.on('connect', namespace='/live2d')
        def handle_live2d_connect():
            self.connected_clients += 1
            self.logger.info(f"Live2D client connected. Total clients: {self.connected_clients}")
            emit('live2d_connected', {
                'status': 'connected',
                'emotion': self.current_emotion,
                'expression': self.emotion_expressions.get(self.current_emotion, 'idle'),
                'vts_connected': self.vts_api_connected
            })
            
            # Broadcast client count to all
            emit('connected_clients', self.connected_clients, broadcast=True, namespace='/live2d')
        
        @self.socketio.on('disconnect', namespace='/live2d')
        def handle_live2d_disconnect():
            self.connected_clients = max(0, self.connected_clients - 1)
            self.logger.info(f"Live2D client disconnected. Total clients: {self.connected_clients}")
            emit('connected_clients', self.connected_clients, broadcast=True, namespace='/live2d')
        
        @self.socketio.on('request_emotion_update', namespace='/live2d')
        def handle_emotion_update(data):
            emotion = data.get('emotion', 'neutral')
            # Run async function in thread
            def update_emotion_async():
                async def async_update():
                    await self.update_emotion(emotion)
                asyncio.run(async_update())
            
            thread = threading.Thread(target=update_emotion_async)
            thread.daemon = True
            thread.start()
    
    async def connect_to_vts(self):
        """Connect to VTube Studio API"""
        if not self.vts_client:
            self.logger.warning("VTube Studio client not available")
            return False
            
        try:
            connected = await self.vts_client.connect()
            if connected:
                self.vts_api_connected = True
                self.logger.info("Connected to VTube Studio API")
                
                # Get available hotkeys and expressions
                await self._load_vts_hotkeys()
                return True
            else:
                self.logger.error("Failed to connect to VTube Studio")
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to VTS: {e}")
            return False
    
    async def _load_vts_hotkeys(self):
        """Load available hotkeys from VTube Studio"""
        try:
            # This would require VTS API implementation to get hotkeys
            # For now, we'll use the emotion mapping
            self.logger.info("VTS hotkeys loaded")
        except Exception as e:
            self.logger.error(f"Error loading VTS hotkeys: {e}")
    
    def start_streaming(self):
        """Start the Live2D model streaming from VTube Studio"""
        if self.is_streaming:
            return
        
        self.is_streaming = True
        self.stream_thread = threading.Thread(target=self._vts_stream_loop, daemon=True)
        self.stream_thread.start()
        self.logger.info("Live2D VTS streaming started")
    
    def stop_streaming(self):
        """Stop the Live2D model streaming"""
        self.is_streaming = False
        if self.stream_thread:
            self.stream_thread.join()
        self.logger.info("Live2D streaming stopped")
    
    def _vts_stream_loop(self):
        """Main streaming loop that captures VTube Studio output"""
        # Note: This is a conceptual implementation
        # Actual implementation depends on VTS API capabilities
        
        while self.is_streaming:
            try:
                # Method 1: Screen capture (requires VTS window to be visible)
                frame_data = self._capture_vts_window()
                
                # Method 2: Use VTS API if it provides frame data (unlikely)
                # frame_data = await self._get_vts_frame_via_api()
                
                # Method 3: Fallback to placeholder with VTS status
                if frame_data is None:
                    frame_data = self._generate_vts_status_frame()
                
                # Broadcast to all connected clients
                if self.connected_clients > 0 and frame_data:
                    self.socketio.emit('live2d_frame', {
                        'frame': frame_data,
                        'emotion': self.current_emotion,
                        'timestamp': time.time(),
                        'vts_connected': self.vts_api_connected
                    }, namespace='/live2d')
                
                # Control frame rate
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                self.logger.error(f"Error in VTS streaming loop: {e}")
                time.sleep(1)  # Wait before retrying
    
    def _capture_vts_window(self):
        """Capture VTube Studio window using screen capture"""
        try:
            import pyautogui
            import pygetwindow as gw
            
            # Find VTube Studio window
            vts_windows = gw.getWindowsWithTitle('VTube Studio')
            if not vts_windows:
                return None
            
            vts_window = vts_windows[0]
            
            # Capture the window
            screenshot = pyautogui.screenshot(region=(
                vts_window.left,
                vts_window.top,
                vts_window.width,
                vts_window.height
            ))
            
            # Convert to base64
            buffered = BytesIO()
            screenshot.save(buffered, format="JPEG", quality=85)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return f"data:image/jpeg;base64,{img_str}"
            
        except ImportError:
            self.logger.warning("Screen capture libraries not available")
            return None
        except Exception as e:
            self.logger.error(f"Screen capture error: {e}")
            return None
    
    def _generate_vts_status_frame(self):
        """Generate a status frame showing VTS connection state"""
        width, height = 400, 300
        image = Image.new('RGB', (width, height), color='lightblue')
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.load_default()
            
            # Title
            draw.text((width//2, height//2 - 40), "VTube Studio", 
                     fill='darkblue', font=font, anchor='mm')
            
            # Connection status
            status = "Connected" if self.vts_api_connected else "Disconnected"
            status_color = "green" if self.vts_api_connected else "red"
            draw.text((width//2, height//2 - 10), f"Status: {status}", 
                     fill=status_color, font=font, anchor='mm')
            
            # Current emotion
            draw.text((width//2, height//2 + 20), f"Emotion: {self.current_emotion}", 
                     fill='black', font=font, anchor='mm')
            
            # Instructions
            draw.text((width//2, height//2 + 50), "Ensure VTS is running", 
                     fill='darkgray', font=font, anchor='mm')
            
        except:
            # Fallback drawing
            draw.text((width//2, height//2 - 20), f"VTS: {status}", 
                     fill='black', anchor='mm')
            draw.text((width//2, height//2 + 10), f"Emotion: {self.current_emotion}", 
                     fill='black', anchor='mm')
        
        # Convert to base64
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/jpeg;base64,{img_str}"
    
    async def update_emotion(self, emotion):
        """Update current emotion and trigger VTube Studio expressions"""
        self.current_emotion = emotion
        expression = self.emotion_expressions.get(emotion, 'idle')
        
        # Update VTube Studio if connected
        if self.vts_client and self.vts_client.is_connected:
            success = await self.vts_client.trigger_expression(expression)
            if success:
                self.logger.info(f"VTS expression triggered: {expression}")
            else:
                self.logger.warning(f"Failed to trigger VTS expression: {expression}")
        
        # Broadcast to all clients
        self.socketio.emit('emotion_updated', {
            'emotion': emotion,
            'expression': expression,
            'vts_connected': self.vts_api_connected
        }, broadcast=True, namespace='/live2d')
        
        self.logger.info(f"Emotion updated to: {emotion} (VTS: {self.vts_api_connected})")