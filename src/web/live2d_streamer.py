import asyncio
import logging
import base64
import json
import threading
import time
from io import BytesIO
from flask_socketio import SocketIO, emit
from PIL import Image, ImageDraw, ImageFont
import cv2
import platform
import subprocess
import sys
import numpy as np

class Live2DStreamer:
    def __init__(self, socketio, vts_client=None):
        self.socketio = socketio
        self.vts_client = vts_client
        self.logger = logging.getLogger(__name__)
        self.is_streaming = False
        self.stream_thread = None
        self.current_emotion = "neutral"
        self.connected_clients = 0
        self.frame_counter = 0
        self.cap = None
        
        # Camera detection state
        self.camera_initialized = False
        self.camera_index = None
        self.camera_retry_count = 0
        self.max_retries = 3
        
        # VTube Studio API integration
        self.vts_api_connected = False
        
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
        
        # Run initial camera scan immediately
        self._perform_initial_camera_scan()
        
        self.setup_socket_handlers()
    
    def _perform_initial_camera_scan(self):
        """Perform initial camera scan when Live2DStreamer starts"""
        self.logger.info("=== PERFORMING INITIAL CAMERA SCAN ===")
        cameras = self._scan_all_cameras()
        
        if cameras:
            self.logger.info(f"🎥 Found {len(cameras)} camera(s) during initial scan:")
            for cam in cameras:
                self.logger.info(f"  - Camera {cam['index']}: {cam['resolution']} @ {cam['fps']}FPS")
            
            # Try to initialize the first camera found
            best_camera = self._find_best_camera()
            if best_camera is not None:
                self.logger.info(f"🚀 Initializing best camera: index {best_camera}")
                self.cap = self._initialize_camera(best_camera)
                if self.cap:
                    self.camera_initialized = True
                    self.camera_index = best_camera
                    self.logger.info("✅ Camera initialized successfully!")
                else:
                    self.logger.warning("❌ Camera initialization failed")
            else:
                self.logger.warning("❌ No suitable camera found")
        else:
            self.logger.warning("❌ No cameras found during initial scan")
        
        self.logger.info("=== INITIAL CAMERA SCAN COMPLETE ===")
    
    def setup_socket_handlers(self):
        """Setup WebSocket handlers for Live2D streaming"""
        @self.socketio.on('connect', namespace='/live2d')
        def handle_live2d_connect():
            self.connected_clients += 1
            self.logger.info(f"Live2D client connected. Total clients: {self.connected_clients}")
            
            # Send current status to new client
            emit('connected', {
                'status': 'connected',
                'emotion': self.current_emotion,
                'expression': self.emotion_expressions.get(self.current_emotion, 'idle'),
                'vts_connected': self.vts_api_connected,
                'camera_available': self.camera_initialized,
                'camera_index': self.camera_index
            })
            
            # Broadcast client count to all
            emit('connected_clients', self.connected_clients, broadcast=True, namespace='/live2d')
            
            # Send camera status update
            emit('camera_status', {
                'available': self.camera_initialized,
                'index': self.camera_index,
                'streaming': self.is_streaming
            })
        
        @self.socketio.on('disconnect', namespace='/live2d')
        def handle_live2d_disconnect():
            self.connected_clients = max(0, self.connected_clients - 1)
            self.logger.info(f"Live2D client disconnected. Total clients: {self.connected_clients}")
            emit('connected_clients', self.connected_clients, broadcast=True, namespace='/live2d')
        
        @self.socketio.on('request_emotion_update', namespace='/live2d')
        def handle_emotion_update(data):
            emotion = data.get('emotion', 'neutral')
            self.logger.info(f"Emotion update requested: {emotion}")
            
            # Update emotion immediately
            def update_emotion_async():
                async def async_update():
                    await self.update_emotion(emotion)
                asyncio.run(async_update())
            
            thread = threading.Thread(target=update_emotion_async)
            thread.daemon = True
            thread.start()

        @self.socketio.on('start_background_stream', namespace='/live2d')
        def handle_start_background_stream():
            self.logger.info("=== STARTING BACKGROUND LIVE2D STREAM ===")
            self.start_streaming()
        
        @self.socketio.on('stop_background_stream', namespace='/live2d')
        def handle_stop_background_stream():
            self.logger.info("Stopping background Live2D stream")
            self.stop_streaming()
        
        @self.socketio.on('scan_cameras', namespace='/live2d')
        def handle_scan_cameras():
            """Manually scan for cameras"""
            self.logger.info("=== MANUAL CAMERA SCAN REQUESTED ===")
            cameras = self._scan_all_cameras()
            
            # Update camera status
            if cameras:
                best_camera = self._find_best_camera()
                if best_camera is not None and not self.camera_initialized:
                    self.cap = self._initialize_camera(best_camera)
                    if self.cap:
                        self.camera_initialized = True
                        self.camera_index = best_camera
                        self.logger.info(f"✅ Camera {best_camera} initialized after manual scan")
            
            emit('camera_scan_results', {
                'cameras_found': cameras,
                'total_cameras': len(cameras),
                'camera_initialized': self.camera_initialized,
                'current_camera_index': self.camera_index
            })
            
            # Also send camera status update
            emit('camera_status', {
                'available': self.camera_initialized,
                'index': self.camera_index,
                'streaming': self.is_streaming
            })
        
        @self.socketio.on('connect_to_vts', namespace='/live2d')
        def handle_connect_to_vts():
            """Connect to VTube Studio"""
            self.logger.info("VTS connection requested via Live2D namespace")
            def connect_async():
                async def async_connect():
                    success = await self.connect_to_vts()
                    if success:
                        emit('vts_connected', {'connected': True}, namespace='/live2d')
                    else:
                        emit('vts_error', {'error': 'Failed to connect to VTS'}, namespace='/live2d')
                asyncio.run(async_connect())
            
            thread = threading.Thread(target=connect_async)
            thread.daemon = True
            thread.start()
        
        @self.socketio.on('get_camera_status', namespace='/live2d')
        def handle_get_camera_status():
            """Send current camera status"""
            emit('camera_status', {
                'available': self.camera_initialized,
                'index': self.camera_index,
                'streaming': self.is_streaming
            })
    
    async def connect_to_vts(self):
        """Connect to VTube Studio API"""
        if not self.vts_client:
            self.logger.warning("VTube Studio client not available")
            return False
            
        try:
            self.logger.info("Attempting to connect to VTube Studio...")
            connected = await self.vts_client.connect()
            if connected:
                self.vts_api_connected = True
                self.logger.info("Connected to VTube Studio API")
                
                # Notify all clients about VTS connection
                self.socketio.emit('vts_connected', {
                    'connected': True,
                    'message': 'VTube Studio connected successfully'
                }, namespace='/live2d')
                
                # Also notify main namespace
                self.socketio.emit('vts_connection_update', {
                    'vts_connected': True,
                    'streaming': self.is_streaming,
                    'modelLoaded': True
                })
                return True
            else:
                self.logger.error("Failed to connect to VTube Studio")
                self.socketio.emit('vts_error', {
                    'error': 'Failed to connect to VTube Studio. Make sure VTube Studio is running and the API is enabled.'
                }, namespace='/live2d')
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to VTS: {e}")
            self.socketio.emit('vts_error', {
                'error': f'Connection error: {str(e)}'
            }, namespace='/live2d')
            return False
    
    def _scan_all_cameras(self):
        """Scan all possible camera indices and return available ones"""
        available_cameras = []
        self.logger.info("🔍 Scanning for available cameras...")
        
        # Check more camera indices with better error handling
        for i in range(10):  # Check first 10 indices
            cap = None
            try:
                # Use DirectShow on Windows for better camera support
                if platform.system() == 'Windows':
                    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(i)
                    
                if cap.isOpened():
                    # Try to read a frame to verify it's working
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        # Get camera properties
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        
                        camera_info = {
                            'index': i,
                            'resolution': f"{width}x{height}",
                            'fps': fps,
                            'status': 'working'
                        }
                        available_cameras.append(camera_info)
                        self.logger.info(f"✅ Found working camera at index {i}: {width}x{height} @ {fps}FPS")
                    else:
                        self.logger.warning(f"⚠️ Camera {i} opened but cannot read frames")
                    cap.release()
                else:
                    self.logger.debug(f"Camera index {i} not available")
            except Exception as e:
                self.logger.warning(f"❌ Error checking camera {i}: {str(e)}")
                if cap:
                    cap.release()
        
        self.logger.info(f"📊 Camera scan complete. Found {len(available_cameras)} cameras")
        return available_cameras
    
    def _find_best_camera(self):
        """Find the best available camera (prioritize virtual cameras)"""
        available_cameras = self._scan_all_cameras()
        
        if not available_cameras:
            self.logger.warning("❌ No cameras found at all")
            return None
        
        self.logger.info(f"🎯 Selecting best camera from {len(available_cameras)} available...")
        
        # Try to identify virtual cameras first
        virtual_camera_indices = []
        other_camera_indices = []
        
        for camera in available_cameras:
            index = camera['index']
            
            # Try to open and check if it might be a virtual camera
            try:
                if platform.system() == 'Windows':
                    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(index)
                    
                if cap.isOpened():
                    # Virtual cameras often have specific resolutions
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    
                    # Common virtual camera resolutions
                    virtual_resolutions = [(1920, 1080), (1280, 720), (2560, 1440), (640, 480)]
                    if (width, height) in virtual_resolutions:
                        virtual_camera_indices.append(index)
                        self.logger.info(f"🖥️  Potential virtual camera at index {index}: {width}x{height}")
                    else:
                        other_camera_indices.append(index)
                        self.logger.info(f"📷 Regular camera at index {index}: {width}x{height}")
                    
                    cap.release()
            except Exception as e:
                self.logger.warning(f"Error checking camera {index}: {e}")
        
        # Prioritize virtual cameras, then other cameras
        if virtual_camera_indices:
            best_index = virtual_camera_indices[0]
            self.logger.info(f"🎯 Selected virtual camera at index {best_index}")
            return best_index
        elif other_camera_indices:
            best_index = other_camera_indices[0]
            self.logger.info(f"🎯 Selected regular camera at index {best_index}")
            return best_index
        
        return None
    
    def _initialize_camera(self, camera_index):
        """Initialize camera with optimal settings"""
        try:
            self.logger.info(f"🚀 Initializing camera at index {camera_index}...")
            
            if platform.system() == 'Windows':
                cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(camera_index)
            
            if not cap.isOpened():
                self.logger.error(f"❌ Failed to open camera at index {camera_index}")
                return None
            
            # Try different camera formats and properties for OBS Virtual Camera
            self.logger.info("🔧 Configuring camera properties for OBS Virtual Camera...")
            
            # Try different resolutions
            resolutions = [(1280, 720), (1920, 1080), (640, 480)]
            for width, height in resolutions:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                time.sleep(0.1)
                
                actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.logger.info(f"  📐 Set resolution: {width}x{height}, Actual: {actual_width}x{actual_height}")
                
                if actual_width > 0 and actual_height > 0:
                    break
            
            # Set other optimal properties
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            
            # Try to set different backends for better color handling
            try:
                cap.set(cv2.CAP_PROP_CONVERT_RGB, 1.0)
            except:
                pass
            
            # Verify camera works by reading multiple frames
            self.logger.info("📸 Testing camera by reading frames...")
            successful_frames = 0
            color_issues = 0
            
            for i in range(5):  # Try 5 times
                ret, frame = cap.read()
                if ret and frame is not None:
                    successful_frames += 1
                    
                    # Check for color issues
                    if frame.shape[2] == 3:  # RGB/BGR
                        # Check if colors are inverted (common OBS issue)
                        blue_channel_mean = frame[:, :, 0].mean()
                        red_channel_mean = frame[:, :, 2].mean()
                        
                        if blue_channel_mean > red_channel_mean + 50:
                            color_issues += 1
                            self.logger.warning(f"  🎨 Frame {i+1}: Possible color inversion detected")
                    
                    self.logger.info(f"  ✅ Frame {i+1}: {frame.shape[1]}x{frame.shape[0]}, Channels: {frame.shape[2]}")
                else:
                    self.logger.warning(f"  ❌ Frame {i+1}: Failed to read")
                time.sleep(0.1)
            
            if successful_frames == 0:
                self.logger.error(f"❌ Camera {camera_index} cannot read any frames")
                cap.release()
                return None
            
            if color_issues > 2:
                self.logger.warning(f"⚠️ Camera {camera_index} has consistent color issues - will apply color correction")
            
            self.logger.info(f"✅ Successfully initialized camera at index {camera_index} ({successful_frames}/5 frames successful, {color_issues} color issues)")
            self.camera_index = camera_index
            self.camera_initialized = True
            return cap
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing camera {camera_index}: {e}")
            return None
    
    def start_streaming(self):
        """Start the Live2D model streaming"""
        if self.is_streaming:
            self.logger.info("📡 Streaming already active")
            return
        
        self.logger.info("=== STARTING LIVE2D STREAMING ===")
        
        # Initialize camera if not already done
        if not self.camera_initialized:
            self.logger.info("🔍 Looking for available cameras...")
            best_camera_index = self._find_best_camera()
            if best_camera_index is not None:
                self.cap = self._initialize_camera(best_camera_index)
                if self.cap:
                    self.logger.info("✅ Camera initialized successfully")
                else:
                    self.logger.info("❌ Camera initialization failed, using placeholder mode")
            else:
                self.logger.info("❌ No camera found, using placeholder mode")
        
        self.is_streaming = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()
        self.logger.info("🎬 Live2D streaming started")
        
        # Notify clients about streaming status
        self.socketio.emit('streaming_status', {
            'streaming': True,
            'camera_available': self.camera_initialized
        }, namespace='/live2d')
    
    def stop_streaming(self):
        """Stop the Live2D model streaming"""
        self.logger.info("🛑 Stopping Live2D streaming")
        self.is_streaming = False
        if self.cap:
            self.cap.release()
            self.cap = None
            self.camera_initialized = False
        if self.stream_thread:
            self.stream_thread.join(timeout=2.0)
        self.logger.info("✅ Live2D streaming stopped")
        
        # Notify clients about streaming status
        self.socketio.emit('streaming_status', {
            'streaming': False,
            'camera_available': False
        }, namespace='/live2d')
    
    def _stream_loop(self):
        """Main streaming loop"""
        last_frame_time = 0
        frame_interval = 0.15  # ~6-7 FPS to prevent flickering
        consecutive_errors = 0
        max_consecutive_errors = 5
        frame_count = 0
        
        self.logger.info("🔄 Starting stream loop...")
        
        while self.is_streaming:
            try:
                current_time = time.time()
                
                # Throttle frame rate
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.01)
                    continue
                
                frame_data, frame_source = self._get_next_frame()
                frame_count += 1
                
                if frame_data:
                    # Log first few frames for debugging
                    if frame_count <= 3:
                        self.logger.info(f"📦 Frame {frame_count}: {frame_source} (size: {len(frame_data)} bytes)")
                    
                    # Broadcast to all connected clients
                    self.socketio.emit('live2d_frame', {
                        'frame': frame_data,
                        'emotion': self.current_emotion,
                        'timestamp': current_time,
                        'vts_connected': self.vts_api_connected,
                        'frame_count': self.frame_counter,
                        'source': frame_source,
                        'camera_available': self.camera_initialized
                    }, namespace='/live2d')
                    
                    last_frame_time = current_time
                    self.frame_counter += 1
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        self.logger.warning(f"⚠️ Too many consecutive errors ({consecutive_errors}), resetting camera")
                        if self.cap:
                            self.cap.release()
                            self.cap = None
                            self.camera_initialized = False
                        consecutive_errors = 0
                
                time.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"❌ Error in streaming loop: {e}")
                time.sleep(0.5)
    
    def _get_next_frame(self):
        """Get the next frame with fallback - FIXED: NO COLOR CONVERSION"""
        # Try to get frame from camera
        if self.cap and self.camera_initialized:
            try:
                # Clear buffer by grabbing a few frames
                for _ in range(2):
                    self.cap.grab()
                
                ret, frame = self.cap.retrieve()
                if ret and frame is not None:
                    self.logger.debug(f"🎨 Processing frame - Shape: {frame.shape}, Type: {frame.dtype}")
                    
                    # FIX: NO COLOR CONVERSION - raw BGR feed is correct!
                    # Send frame as-is without any color conversion
                    frame_rgb = frame
                    
                    frame_data = self._frame_to_base64(frame_rgb)
                    if frame_data:
                        return frame_data, "virtual_camera"
                    else:
                        self.logger.warning("❌ Failed to convert camera frame to base64")
                else:
                    self.logger.warning("📷 Camera returned no frame")
                
            except Exception as e:
                self.logger.warning(f"📷 Camera read error: {e}")
        
        # Generate placeholder
        frame_data = self._generate_enhanced_vts_frame()
        return frame_data, "placeholder"
    
    def _frame_to_base64(self, frame):
        """Convert OpenCV frame to base64"""
        try:
            # Resize for performance
            h, w = frame.shape[:2]
            if w > 1280 or h > 720:
                frame = cv2.resize(frame, (1280, 720))
            
            # Use better JPEG quality and progressive encoding
            success, encoded_image = cv2.imencode('.jpg', frame, [
                cv2.IMWRITE_JPEG_QUALITY, 90,
                cv2.IMWRITE_JPEG_PROGRESSIVE, 1
            ])
            
            if success:
                img_str = base64.b64encode(encoded_image).decode()
                return f"data:image/jpeg;base64,{img_str}"
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error converting frame: {e}")
            return None
    
    def _generate_enhanced_vts_frame(self):
        """Generate enhanced placeholder with setup instructions"""
        width, height = 800, 600
        image = Image.new('RGB', (width, height), color='#6366f1')
        draw = ImageDraw.Draw(image)
        
        try:
            # Try to load a font, fallback to default
            try:
                font_large = ImageFont.truetype("arial.ttf", 24)
                font_medium = ImageFont.truetype("arial.ttf", 16)
                font_small = ImageFont.truetype("arial.ttf", 14)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            center_x, center_y = width // 2, height // 2
            
            # Title
            draw.text((center_x, 50), "Lumi AI Companion - Virtual Camera Setup", 
                     fill='white', font=font_large, anchor='mm')
            
            # Status
            status_y = 100
            if self.camera_initialized:
                status_text = "✅ Virtual Camera Connected"
                status_color = "#10b981"
            elif self.vts_api_connected:
                status_text = "⚠️ VTS Connected - Camera Setup Needed"
                status_color = "#f59e0b"
            else:
                status_text = "❌ VTS & Camera Setup Needed"
                status_color = "#ef4444"
            
            draw.text((center_x, status_y), status_text, 
                     fill=status_color, font=font_medium, anchor='mm')
            
            # VTS Status
            vts_status = "✅ Connected" if self.vts_api_connected else "❌ Disconnected"
            vts_color = "#10b981" if self.vts_api_connected else "#ef4444"
            draw.text((center_x, status_y + 30), f"VTube Studio: {vts_status}", 
                     fill=vts_color, font=font_medium, anchor='mm')
            
            # Camera Status
            cam_status = "✅ Available" if self.camera_initialized else "❌ Not Found"
            cam_color = "#10b981" if self.camera_initialized else "#ef4444"
            draw.text((center_x, status_y + 60), f"Virtual Camera: {cam_status}", 
                     fill=cam_color, font=font_medium, anchor='mm')
            
            # Setup Instructions
            instructions = [
                "To enable virtual camera:",
                "",
                "Option 1: VTube Studio Virtual Camera",
                "1. Open VTube Studio → Settings → Virtual Camera",
                "2. Enable 'Virtual Camera' and click 'Start'",
                "3. Restart Lumi AI",
                "",
                "Option 2: OBS Virtual Camera (Recommended)",
                "1. Install OBS Studio (free)",
                "2. Add VTube Studio as Window Capture source",
                "3. Tools → VirtualCam → Start",
                "4. Restart Lumi AI",
                "",
                "After setup, click 'Scan Cameras' in the web interface"
            ]
            
            # Draw instructions
            instruction_y = 200
            line_height = 20
            for i, line in enumerate(instructions):
                y_pos = instruction_y + (i * line_height)
                if y_pos < height - 50:  # Don't draw beyond image bounds
                    font = font_small if i > 1 else font_medium
                    draw.text((50, y_pos), line, fill='white', font=font)
            
        except Exception as e:
            self.logger.error(f"❌ Error generating placeholder: {e}")
            draw.text((center_x, height//2), "Lumi AI - Camera Setup Required", 
                     fill='white', anchor='mm')
        
        # Convert to base64
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=90)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/jpeg;base64,{img_str}"
    
    async def update_emotion(self, emotion):
        """Update current emotion"""
        self.current_emotion = emotion
        expression = self.emotion_expressions.get(emotion, 'idle')
        
        self.logger.info(f"🎭 Updating emotion to: {emotion} -> {expression}")
        
        if self.vts_client and self.vts_api_connected:
            try:
                success = await self.vts_client.trigger_expression(expression)
                if success:
                    self.logger.info(f"✅ VTS expression triggered: {expression}")
                else:
                    self.logger.warning(f"⚠️ Failed to trigger VTS expression: {expression}")
            except Exception as e:
                self.logger.error(f"❌ Error triggering VTS expression: {e}")
        
        self.socketio.emit('emotion_updated', {
            'emotion': emotion,
            'expression': expression,
            'vts_connected': self.vts_api_connected
        }, broadcast=True, namespace='/live2d')

    def get_stream_status(self):
        """Get current streaming status"""
        return {
            'streaming': self.is_streaming,
            'vts_connected': self.vts_api_connected,
            'camera_available': self.camera_initialized,
            'camera_index': self.camera_index,
            'connected_clients': self.connected_clients,
            'current_emotion': self.current_emotion
        }