from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import logging
import asyncio
import threading
import json
from .live2d_streamer import Live2DStreamer
from .theme_manager import ThemeManager
from .dashboard_manager import DashboardManager

class WebServer:
    def __init__(self, ai_engine, host='0.0.0.0', port=5000):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'lumi_secret_key_2024'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')
        CORS(self.app)
        
        self.host = host
        self.port = port
        self.ai_engine = ai_engine
        self.logger = logging.getLogger(__name__)
        
        # Initialize enhanced systems
        self.live2d_streamer = Live2DStreamer(self.socketio, ai_engine.vts_client)
        self.theme_manager = ThemeManager()
        self.dashboard_manager = DashboardManager(ai_engine)
        
        self.setup_routes()
        self.setup_socket_handlers()
    
    def setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/api/status')
        def api_status():
            return jsonify({
                'status': 'online',
                'name': 'Lumi AI Companion',
                'version': '2.0',
                'features': {
                    'live2d_streaming': True,
                    'theme_system': True,
                    'advanced_dashboard': True,
                    'voice_chat': self.ai_engine.stt_engine is not None and self.ai_engine.stt_engine.is_initialized,
                    'emotional_ai': True
                }
            })
        
        @self.app.route('/api/chat', methods=['POST'])
        async def api_chat():
            try:
                data = request.get_json()
                user_input = data.get('message', '')
                
                if not user_input:
                    return jsonify({'error': 'No message provided'}), 400
                
                # Generate response
                response = await self.ai_engine.generate_response(user_input)
                
                # Update dashboard
                await self.dashboard_manager.update_dashboard_data({
                    "user_input": user_input,
                    "ai_response": response,
                    "emotion": self.ai_engine.current_emotion,
                    "sentiment": 0.5  # Would come from sentiment analysis
                })
                
                return jsonify({
                    'response': response,
                    'user_input': user_input
                })
                
            except Exception as e:
                self.logger.error(f"API chat error: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/character')
        def api_character():
            if self.ai_engine.character_data:
                return jsonify(self.ai_engine.character_data)
            return jsonify({'error': 'Character not loaded'}), 404
        
        @self.app.route('/api/stats')
        async def api_stats():
            try:
                stats = await self.ai_engine.get_advanced_stats()
                return jsonify(stats)
            except Exception as e:
                self.logger.error(f"API stats error: {e}")
                return jsonify({'error': 'Failed to get stats'}), 500
        
        @self.app.route('/api/dashboard')
        async def api_dashboard():
            try:
                metrics = await self.dashboard_manager.get_dashboard_metrics()
                visualization_data = await self.dashboard_manager.get_visualization_data()
                return jsonify({
                    'metrics': metrics,
                    'visualizations': visualization_data
                })
            except Exception as e:
                self.logger.error(f"Dashboard API error: {e}")
                return jsonify({'error': 'Failed to get dashboard data'}), 500
        
        @self.app.route('/api/themes')
        def api_themes():
            try:
                themes = self.theme_manager.get_available_themes()
                current_theme = self.theme_manager.current_theme
                theme_css = self.theme_manager.get_theme_css()
                return jsonify({
                    'themes': themes,
                    'current_theme': current_theme,
                    'theme_css': theme_css
                })
            except Exception as e:
                self.logger.error(f"Themes API error: {e}")
                return jsonify({'error': 'Failed to get themes'}), 500
        
        @self.app.route('/api/themes/<theme_name>', methods=['POST'])
        def api_set_theme(theme_name):
            try:
                success = self.theme_manager.set_theme(theme_name)
                if success:
                    theme_css = self.theme_manager.get_theme_css()
                    return jsonify({
                        'success': True,
                        'theme': theme_name,
                        'theme_css': theme_css
                    })
                else:
                    return jsonify({'error': 'Theme not found'}), 404
            except Exception as e:
                self.logger.error(f"Theme set error: {e}")
                return jsonify({'error': 'Failed to set theme'}), 500
    
    def setup_socket_handlers(self):
        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info('Client connected via WebSocket')
            emit('connected', {'message': 'Connected to Lumi AI Companion'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.info('Client disconnected')
        
        @self.socketio.on('chat_message')
        def handle_chat_message(data):
            self.logger.info(f"Received chat message: {data}")
            
            def generate_response():
                async def async_generate():
                    try:
                        response = await self.ai_engine.generate_response(data['message'])
                        
                        # Update dashboard
                        await self.dashboard_manager.update_dashboard_data({
                            "user_input": data['message'],
                            "ai_response": response,
                            "emotion": self.ai_engine.current_emotion,
                            "sentiment": 0.5
                        })
                        
                        # Send response
                        self.socketio.emit('chat_response', {
                            'response': response,
                            'user_input': data['message']
                        })
                        
                        # Send dashboard update
                        dashboard_data = await self.dashboard_manager.get_dashboard_metrics()
                        self.socketio.emit('dashboard_update', dashboard_data)
                        
                    except Exception as e:
                        self.logger.error(f"Error generating response: {e}")
                        self.socketio.emit('chat_error', {
                            'error': 'Failed to generate response'
                        })
                
                asyncio.run(async_generate())
            
            thread = threading.Thread(target=generate_response)
            thread.daemon = True
            thread.start()
        
        @self.socketio.on('update_emotion')
        def handle_update_emotion(data):
            emotion = data.get('emotion', 'neutral')
            self.live2d_streamer.update_emotion(emotion)
            emit('emotion_updated', {'emotion': emotion}, broadcast=True)
        
        @self.socketio.on('request_dashboard_data')
        def handle_dashboard_request():
            def send_dashboard_data():
                async def async_send():
                    try:
                        dashboard_data = await self.dashboard_manager.get_dashboard_metrics()
                        self.socketio.emit('dashboard_data', dashboard_data)
                    except Exception as e:
                        self.logger.error(f"Error sending dashboard data: {e}")
                
                asyncio.run(async_send())
            
            thread = threading.Thread(target=send_dashboard_data)
            thread.daemon = True
            thread.start()
        
        @self.socketio.on('change_theme')
        def handle_theme_change(data):
            theme_name = data.get('theme', 'default')
            success = self.theme_manager.set_theme(theme_name)
            if success:
                theme_css = self.theme_manager.get_theme_css()
                emit('theme_changed', {
                    'theme': theme_name,
                    'theme_css': theme_css
                }, broadcast=True)
    
    def run(self):
        self.logger.info(f"Starting Enhanced WebUI on {self.host}:{self.port}")
        self.logger.info("Features: Themes, Dashboard, Live2D Streaming")
        self.socketio.run(self.app, host=self.host, port=self.port, debug=False)