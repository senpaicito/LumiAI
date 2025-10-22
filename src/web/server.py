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
from config.settings_manager import settings

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
            # Get plugin information if available
            plugin_info = []
            if self.ai_engine.plugin_manager:
                plugin_info = self.ai_engine.plugin_manager.get_plugin_info()
            
            return jsonify({
                'status': 'online',
                'name': 'Lumi AI Companion',
                'version': '2.0',
                'features': {
                    'live2d_streaming': True,
                    'theme_system': True,
                    'advanced_dashboard': True,
                    'voice_chat': self.ai_engine.stt_engine is not None and self.ai_engine.stt_engine.is_initialized,
                    'emotional_ai': True,
                    'plugin_system': self.ai_engine.plugin_manager is not None
                },
                'plugins': {
                    'loaded': len(plugin_info),
                    'enabled': len([p for p in plugin_info if p['enabled']]),
                    'list': plugin_info
                },
                'config': {
                    'ollama_model': settings.OLLAMA_MODEL,
                    'discord_enabled': settings.get('discord.enabled', False),
                    'vts_enabled': settings.get('vtube_studio.enabled', False)
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
                
                # Add plugin metrics if available
                if self.ai_engine.plugin_manager:
                    plugin_metrics = await self.ai_engine.plugin_manager.dispatch_dashboard_update()
                    metrics['plugin_metrics'] = plugin_metrics
                
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
        
        # Configuration API Routes
        @self.app.route('/api/config', methods=['GET', 'POST'])
        def api_config():
            """Get or update entire configuration"""
            if request.method == 'GET':
                return jsonify(settings._config)
            else:
                try:
                    new_config = request.get_json()
                    # Validate and update configuration
                    for section, values in new_config.items():
                        if section in settings._config:
                            for key, value in values.items():
                                settings.set(f"{section}.{key}", value)
                    return jsonify({'success': True, 'message': 'Configuration updated'})
                except Exception as e:
                    self.logger.error(f"Config update error: {e}")
                    return jsonify({'error': 'Invalid configuration'}), 400
        
        @self.app.route('/api/config/<path:key>', methods=['GET', 'POST'])
        def api_config_value(key):
            """Get or update specific configuration value"""
            if request.method == 'GET':
                value = settings.get(key)
                return jsonify({'key': key, 'value': value})
            else:
                try:
                    data = request.get_json()
                    value = data.get('value')
                    settings.set(key, value)
                    return jsonify({'success': True, 'message': f'Configuration {key} updated'})
                except Exception as e:
                    self.logger.error(f"Config value update error: {e}")
                    return jsonify({'error': str(e)}), 400
        
        # Plugin Management API Routes
        @self.app.route('/api/plugins')
        def api_get_plugins():
            """Get information about all plugins"""
            if not self.ai_engine.plugin_manager:
                return jsonify({'error': 'Plugin system not available'}), 503
            
            plugin_info = self.ai_engine.plugin_manager.get_plugin_info()
            return jsonify({
                'plugins': plugin_info,
                'total_plugins': len(plugin_info),
                'enabled_plugins': len([p for p in plugin_info if p['enabled']])
            })
        
        @self.app.route('/api/plugins/<plugin_name>/enable', methods=['POST'])
        async def api_enable_plugin(plugin_name):
            """Enable a specific plugin"""
            if not self.ai_engine.plugin_manager:
                return jsonify({'error': 'Plugin system not available'}), 503
            
            success = await self.ai_engine.plugin_manager.enable_plugin(plugin_name)
            if success:
                # Save plugin configuration
                await self.ai_engine.plugin_manager.registry.save_config()
                return jsonify({'success': True, 'message': f'Plugin {plugin_name} enabled'})
            else:
                return jsonify({'error': f'Failed to enable plugin {plugin_name}'}), 400
        
        @self.app.route('/api/plugins/<plugin_name>/disable', methods=['POST'])
        async def api_disable_plugin(plugin_name):
            """Disable a specific plugin"""
            if not self.ai_engine.plugin_manager:
                return jsonify({'error': 'Plugin system not available'}), 503
            
            success = await self.ai_engine.plugin_manager.disable_plugin(plugin_name)
            if success:
                # Save plugin configuration
                await self.ai_engine.plugin_manager.registry.save_config()
                return jsonify({'success': True, 'message': f'Plugin {plugin_name} disabled'})
            else:
                return jsonify({'error': f'Failed to disable plugin {plugin_name}'}), 400
        
        @self.app.route('/api/plugins/<plugin_name>/config', methods=['GET', 'POST'])
        async def api_plugin_config(plugin_name):
            """Get or update plugin configuration"""
            if not self.ai_engine.plugin_manager:
                return jsonify({'error': 'Plugin system not available'}), 503
            
            if request.method == 'GET':
                config = self.ai_engine.plugin_manager.registry.get_plugin_config(plugin_name)
                return jsonify({'config': config})
            
            elif request.method == 'POST':
                try:
                    new_config = request.get_json()
                    success = self.ai_engine.plugin_manager.registry.update_plugin_config(plugin_name, new_config)
                    if success:
                        # Update the plugin instance's config
                        plugin = self.ai_engine.plugin_manager.plugins.get(plugin_name)
                        if plugin:
                            plugin.config = new_config
                        
                        await self.ai_engine.plugin_manager.registry.save_config()
                        return jsonify({'success': True, 'message': f'Plugin {plugin_name} configuration updated'})
                    else:
                        return jsonify({'error': f'Plugin {plugin_name} not found'}), 404
                except Exception as e:
                    self.logger.error(f"Error updating plugin config: {e}")
                    return jsonify({'error': 'Invalid configuration'}), 400
    
    def setup_socket_handlers(self):
        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info('Client connected via WebSocket')
            # Send plugin status on connect
            if self.ai_engine.plugin_manager:
                plugin_info = self.ai_engine.plugin_manager.get_plugin_info()
                self.socketio.emit('plugin_status', {'plugins': plugin_info})
            self.socketio.emit('connected', {'message': 'Connected to Lumi AI Companion'})
        
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
                        
                        # Add plugin metrics
                        if self.ai_engine.plugin_manager:
                            plugin_metrics = await self.ai_engine.plugin_manager.dispatch_dashboard_update()
                            dashboard_data['plugin_metrics'] = plugin_metrics
                        
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
            self.socketio.emit('emotion_updated', {'emotion': emotion}, broadcast=True)
        
        @self.socketio.on('request_dashboard_data')
        def handle_dashboard_request():
            def send_dashboard_data():
                async def async_send():
                    try:
                        dashboard_data = await self.dashboard_manager.get_dashboard_metrics()
                        
                        # Add plugin metrics
                        if self.ai_engine.plugin_manager:
                            plugin_metrics = await self.ai_engine.plugin_manager.dispatch_dashboard_update()
                            dashboard_data['plugin_metrics'] = plugin_metrics
                        
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
                self.socketio.emit('theme_changed', {
                    'theme': theme_name,
                    'theme_css': theme_css
                }, broadcast=True)
        
        # Configuration Socket Events
        @self.socketio.on('get_config')
        def handle_get_config():
            """Send current configuration to client"""
            self.socketio.emit('config_data', {'config': settings._config})
        
        @self.socketio.on('update_config')
        def handle_update_config(data):
            """Update configuration via socket"""
            key = data.get('key')
            value = data.get('value')
            
            if not key:
                self.socketio.emit('config_error', {'error': 'No key provided'})
                return
            
            try:
                old_value = settings.get(key)
                settings.set(key, value)
                self.socketio.emit('config_updated', {
                    'key': key,
                    'old_value': old_value,
                    'new_value': value
                }, broadcast=True)
                self.logger.info(f"Configuration updated: {key} = {value}")
            except Exception as e:
                self.logger.error(f"Config update error: {e}")
                self.socketio.emit('config_error', {'error': str(e)})
        
        # Plugin Management Socket Events
        @self.socketio.on('get_plugins')
        def handle_get_plugins():
            """Send plugin information to client"""
            if self.ai_engine.plugin_manager:
                plugin_info = self.ai_engine.plugin_manager.get_plugin_info()
                self.socketio.emit('plugin_list', {'plugins': plugin_info})
        
        @self.socketio.on('enable_plugin')
        def handle_enable_plugin(data):
            """Enable a plugin via socket"""
            plugin_name = data.get('plugin_name')
            if not plugin_name or not self.ai_engine.plugin_manager:
                self.socketio.emit('plugin_error', {'error': 'Invalid request'})
                return
            
            def enable_plugin_async():
                async def async_enable():
                    try:
                        success = await self.ai_engine.plugin_manager.enable_plugin(plugin_name)
                        if success:
                            await self.ai_engine.plugin_manager.registry.save_config()
                            plugin_info = self.ai_engine.plugin_manager.get_plugin_info()
                            # Use self.socketio.emit instead of emit() for thread safety
                            self.socketio.emit('plugin_enabled', {
                                'plugin_name': plugin_name,
                                'plugins': plugin_info
                            }, broadcast=True)
                        else:
                            self.socketio.emit('plugin_error', {'error': f'Failed to enable {plugin_name}'})
                    except Exception as e:
                        self.logger.error(f"Error enabling plugin: {e}")
                        self.socketio.emit('plugin_error', {'error': str(e)})
                
                asyncio.run(async_enable())
            
            thread = threading.Thread(target=enable_plugin_async)
            thread.daemon = True
            thread.start()
        
        @self.socketio.on('disable_plugin')
        def handle_disable_plugin(data):
            """Disable a plugin via socket"""
            plugin_name = data.get('plugin_name')
            if not plugin_name or not self.ai_engine.plugin_manager:
                self.socketio.emit('plugin_error', {'error': 'Invalid request'})
                return
            
            def disable_plugin_async():
                async def async_disable():
                    try:
                        success = await self.ai_engine.plugin_manager.disable_plugin(plugin_name)
                        if success:
                            await self.ai_engine.plugin_manager.registry.save_config()
                            plugin_info = self.ai_engine.plugin_manager.get_plugin_info()
                            # Use self.socketio.emit instead of emit() for thread safety
                            self.socketio.emit('plugin_disabled', {
                                'plugin_name': plugin_name,
                                'plugins': plugin_info
                            }, broadcast=True)
                        else:
                            self.socketio.emit('plugin_error', {'error': f'Failed to disable {plugin_name}'})
                    except Exception as e:
                        self.logger.error(f"Error disabling plugin: {e}")
                        self.socketio.emit('plugin_error', {'error': str(e)})
                
                asyncio.run(async_disable())
            
            thread = threading.Thread(target=disable_plugin_async)
            thread.daemon = True
            thread.start()
        
        @self.socketio.on('update_plugin_config')
        def handle_update_plugin_config(data):
            """Update plugin configuration via socket"""
            plugin_name = data.get('plugin_name')
            config = data.get('config')
            
            if not plugin_name or not config or not self.ai_engine.plugin_manager:
                self.socketio.emit('plugin_error', {'error': 'Invalid request'})
                return
            
            def update_plugin_config_async():
                async def async_update():
                    try:
                        success = self.ai_engine.plugin_manager.registry.update_plugin_config(plugin_name, config)
                        if success:
                            # Update the plugin instance's config
                            plugin = self.ai_engine.plugin_manager.plugins.get(plugin_name)
                            if plugin:
                                plugin.config = config
                            
                            await self.ai_engine.plugin_manager.registry.save_config()
                            self.socketio.emit('plugin_config_updated', {
                                'plugin_name': plugin_name,
                                'config': config
                            }, broadcast=True)
                        else:
                            self.socketio.emit('plugin_error', {'error': f'Plugin {plugin_name} not found'})
                    except Exception as e:
                        self.logger.error(f"Error updating plugin config: {e}")
                        self.socketio.emit('plugin_error', {'error': str(e)})
                
                asyncio.run(async_update())
            
            thread = threading.Thread(target=update_plugin_config_async)
            thread.daemon = True
            thread.start()
    
    def run(self):
        self.logger.info(f"Starting Enhanced WebUI on {self.host}:{self.port}")
        self.logger.info("Features: Themes, Dashboard, Live2D Streaming, Plugin System, Configuration Management")
        self.socketio.run(self.app, host=self.host, port=self.port, debug=False)