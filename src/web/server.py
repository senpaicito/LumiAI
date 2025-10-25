from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import logging
import asyncio
import threading
import json
import os
import sys
import time
import cv2
import base64
from io import BytesIO

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)  # This goes up to src/web -> src
sys.path.insert(0, src_dir)

# Now import from the correct paths
from src.web.live2d_streamer import Live2DStreamer
from src.web.theme_manager import ThemeManager
from src.web.dashboard_manager import DashboardManager
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
        
        # MJPG streaming state
        self.mjpg_streaming = False
        self.mjpg_frame = None
        self.mjpg_frame_lock = threading.Lock()
        self.mjpg_frame_available = threading.Event()
        
        # Plugin web UI state
        self.plugin_pages = []
        self.plugin_assets = {
            'css': [],
            'js': [],
            'html_head': ''
        }
        
        # Initialize enhanced systems
        self.live2d_streamer = Live2DStreamer(self.socketio, ai_engine.vts_client)
        self.theme_manager = ThemeManager()
        self.dashboard_manager = DashboardManager(ai_engine)
        
        self.setup_routes()
        self.setup_socket_handlers()
        self.setup_mjpg_routes()
        
        # Start MJPG frame update thread
        self.start_mjpg_frame_updater()
    
    # NEW: Plugin Web UI Methods
    async def register_plugin_routes(self):
        """Register web routes from all plugins"""
        if not hasattr(self.ai_engine, 'plugin_manager') or not self.ai_engine.plugin_manager:
            self.logger.info("No plugin manager available for route registration")
            return
        
        self.logger.info("🔄 Registering plugin web routes...")
        
        for plugin_name, plugin in self.ai_engine.plugin_manager.plugins.items():
            try:
                # Register web routes
                if hasattr(plugin, 'get_web_routes'):
                    routes = await plugin.get_web_routes()
                    for route in routes:
                        self.app.add_url_rule(
                            f"/plugin/{plugin_name}{route['path']}",
                            endpoint=f"plugin_{plugin_name}_{route['name']}",
                            view_func=route['view_func'],
                            methods=route.get('methods', ['GET'])
                        )
                        self.logger.info(f"✅ Registered plugin route: /plugin/{plugin_name}{route['path']}")
                
                # Register static files
                if hasattr(plugin, 'get_static_files'):
                    static_files = await plugin.get_static_files()
                    for url_path, file_path in static_files.items():
                        if file_path.exists():
                            self.app.static(
                                f"/static/plugins/{plugin_name}/{url_path}",
                                str(file_path)
                            )
                            self.logger.info(f"✅ Mounted plugin static files: /static/plugins/{plugin_name}/{url_path}")
                        else:
                            self.logger.warning(f"❌ Static file not found: {file_path}")
                
                # Collect plugin pages for navigation
                if hasattr(plugin, 'get_plugin_pages'):
                    pages = await plugin.get_plugin_pages()
                    for page in pages:
                        page['plugin'] = plugin_name
                        self.plugin_pages.append(page)
                        self.logger.info(f"✅ Added plugin page: {page.get('name', 'Unnamed')}")
                
                # Collect UI assets
                if hasattr(plugin, 'get_ui_assets'):
                    assets = await plugin.get_ui_assets()
                    if 'css' in assets:
                        self.plugin_assets['css'].extend(assets['css'])
                    if 'js' in assets:
                        self.plugin_assets['js'].extend(assets['js'])
                    if 'html_head' in assets:
                        self.plugin_assets['html_head'] += assets['html_head']
                        
            except Exception as e:
                self.logger.error(f"❌ Error registering routes for plugin {plugin_name}: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
    
    def get_plugin_template_context(self):
        """Get template context from all plugins"""
        context = {
            'plugin_pages': self.plugin_pages,
            'plugin_assets': self.plugin_assets
        }
        
        if not hasattr(self.ai_engine, 'plugin_manager') or not self.ai_engine.plugin_manager:
            return context
        
        for plugin_name, plugin in self.ai_engine.plugin_manager.plugins.items():
            try:
                if hasattr(plugin, 'get_template_variables'):
                    plugin_context = plugin.get_template_variables()
                    if asyncio.iscoroutine(plugin_context):
                        plugin_context = asyncio.run(plugin_context)
                    context[f'plugin_{plugin_name}'] = plugin_context
            except Exception as e:
                self.logger.error(f"Error getting template context from {plugin_name}: {e}")
        
        return context

    def setup_routes(self):
        @self.app.route('/')
        def index():
            # Get plugin context for template
            plugin_context = self.get_plugin_template_context()
            return render_template('index.html', **plugin_context)
        
        # NEW: Plugin pages route
        @self.app.route('/plugins')
        def plugin_hub():
            """Main plugin hub page"""
            plugin_context = self.get_plugin_template_context()
            return render_template('plugins.html', **plugin_context)
        
        # NEW: Individual plugin page route
        @self.app.route('/plugins/<plugin_name>')
        def plugin_page(plugin_name):
            """Individual plugin page"""
            plugin_context = self.get_plugin_template_context()
            
            # Find the specific plugin page
            current_plugin_page = None
            for page in self.plugin_pages:
                if page.get('plugin') == plugin_name and page.get('default', False):
                    current_plugin_page = page
                    break
            
            return render_template('plugin_page.html', 
                                plugin_name=plugin_name,
                                plugin_page=current_plugin_page,
                                **plugin_context)
        
        @self.app.route('/api/status')
        def api_status():
            # Get plugin information if available
            plugin_info = []
            plugin_webui_count = 0
            if hasattr(self.ai_engine, 'plugin_manager') and self.ai_engine.plugin_manager:
                plugin_info = self.ai_engine.plugin_manager.get_plugin_info()
                plugin_webui_count = len([p for p in self.plugin_pages])
            
            # Get VTS status
            vts_status = self.live2d_streamer.get_stream_status()
            
            return jsonify({
                'status': 'online',
                'name': 'Lumi AI Companion',
                'version': '2.0',
                'features': {
                    'live2d_streaming': True,
                    'theme_system': True,
                    'advanced_dashboard': True,
                    'voice_chat': self.ai_engine.stt_engine is not None and hasattr(self.ai_engine.stt_engine, 'is_initialized') and self.ai_engine.stt_engine.is_initialized,
                    'emotional_ai': True,
                    'plugin_system': hasattr(self.ai_engine, 'plugin_manager') and self.ai_engine.plugin_manager is not None,
                    'plugin_webui': plugin_webui_count > 0,
                    'vts_integration': vts_status['vts_connected'],
                    'mjpg_streaming': True
                },
                'plugins': {
                    'loaded': len(plugin_info),
                    'enabled': len([p for p in plugin_info if p.get('enabled', False)]),
                    'webui_pages': plugin_webui_count,
                    'list': plugin_info
                },
                'config': {
                    'ollama_model': settings.OLLAMA_MODEL,
                    'discord_enabled': settings.get('discord.enabled', False),
                    'vts_enabled': settings.get('vtube_studio.enabled', False)
                },
                'vts_status': vts_status
            })
        
        # NEW: Plugin web UI API endpoints
        @self.app.route('/api/plugins/webui')
        def api_plugin_webui():
            """Get plugin web UI information"""
            return jsonify({
                'pages': self.plugin_pages,
                'assets': self.plugin_assets
            })
        
        @self.app.route('/api/plugins/<plugin_name>/webui')
        def api_plugin_webui_info(plugin_name):
            """Get specific plugin web UI information"""
            plugin_pages = [p for p in self.plugin_pages if p.get('plugin') == plugin_name]
            return jsonify({
                'plugin_name': plugin_name,
                'pages': plugin_pages
            })
        
        @self.app.route('/api/vts_status')
        def api_vts_status():
            """Get VTube Studio connection status"""
            try:
                status = self.live2d_streamer.get_stream_status()
                return jsonify(status)
            except Exception as e:
                self.logger.error(f"VTS status API error: {e}")
                return jsonify({'error': 'Failed to get VTS status'}), 500
        
        @self.app.route('/api/chat', methods=['POST'])
        def api_chat():
            try:
                data = request.get_json()
                user_input = data.get('message', '')
                
                if not user_input:
                    return jsonify({'error': 'No message provided'}), 400
                
                # Generate response using asyncio in thread
                def generate_response():
                    async def async_generate():
                        try:
                            response = await self.ai_engine.generate_response(user_input)
                            
                            # Update dashboard
                            await self.dashboard_manager.update_dashboard_data({
                                "user_input": user_input,
                                "ai_response": response,
                                "emotion": self.ai_engine.current_emotion,
                                "sentiment": 0.5
                            })
                            
                            return response
                        except Exception as e:
                            self.logger.error(f"Error generating response: {e}")
                            return "I'm having trouble thinking right now. Could you try again?"
                    
                    return asyncio.run(async_generate())
                
                # Run in thread to avoid blocking
                response = generate_response()
                
                return jsonify({
                    'response': response,
                    'user_input': user_input
                })
                
            except Exception as e:
                self.logger.error(f"API chat error: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/api/character')
        def api_character():
            if hasattr(self.ai_engine, 'character_data') and self.ai_engine.character_data:
                return jsonify(self.ai_engine.character_data)
            return jsonify({'error': 'Character not loaded'}), 404
        
        @self.app.route('/api/stats')
        def api_stats():
            try:
                # Run async function in thread
                def get_stats():
                    async def async_get():
                        return await self.ai_engine.get_advanced_stats()
                    return asyncio.run(async_get())
                
                stats = get_stats()
                return jsonify(stats)
            except Exception as e:
                self.logger.error(f"API stats error: {e}")
                return jsonify({'error': 'Failed to get stats'}), 500
        
        @self.app.route('/api/dashboard')
        def api_dashboard():
            try:
                # Run async function in thread
                def get_dashboard_data():
                    async def async_get():
                        metrics = await self.dashboard_manager.get_dashboard_metrics()
                        visualization_data = await self.dashboard_manager.get_visualization_data()
                        
                        # Add plugin metrics if available
                        if hasattr(self.ai_engine, 'plugin_manager') and self.ai_engine.plugin_manager:
                            plugin_metrics = await self.ai_engine.plugin_manager.dispatch_dashboard_update()
                            metrics['plugin_metrics'] = plugin_metrics
                        
                        return {
                            'metrics': metrics,
                            'visualizations': visualization_data
                        }
                    return asyncio.run(async_get())
                
                data = get_dashboard_data()
                return jsonify(data)
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
            if not hasattr(self.ai_engine, 'plugin_manager') or not self.ai_engine.plugin_manager:
                return jsonify({'error': 'Plugin system not available'}), 503
            
            plugin_info = self.ai_engine.plugin_manager.get_plugin_info()
            return jsonify({
                'plugins': plugin_info,
                'total_plugins': len(plugin_info),
                'enabled_plugins': len([p for p in plugin_info if p.get('enabled', False)]),
                'webui_pages': len(self.plugin_pages)
            })
        
        @self.app.route('/api/plugins/<plugin_name>/enable', methods=['POST'])
        def api_enable_plugin(plugin_name):
            """Enable a specific plugin"""
            if not hasattr(self.ai_engine, 'plugin_manager') or not self.ai_engine.plugin_manager:
                return jsonify({'error': 'Plugin system not available'}), 503
            
            def enable_plugin():
                async def async_enable():
                    success = await self.ai_engine.plugin_manager.enable_plugin(plugin_name)
                    if success:
                        await self.ai_engine.plugin_manager.registry.save_config()
                    return success
                return asyncio.run(async_enable())
            
            success = enable_plugin()
            if success:
                return jsonify({'success': True, 'message': f'Plugin {plugin_name} enabled'})
            else:
                return jsonify({'error': f'Failed to enable plugin {plugin_name}'}), 400
        
        @self.app.route('/api/plugins/<plugin_name>/disable', methods=['POST'])
        def api_disable_plugin(plugin_name):
            """Disable a specific plugin"""
            if not hasattr(self.ai_engine, 'plugin_manager') or not self.ai_engine.plugin_manager:
                return jsonify({'error': 'Plugin system not available'}), 503
            
            def disable_plugin():
                async def async_disable():
                    success = await self.ai_engine.plugin_manager.disable_plugin(plugin_name)
                    if success:
                        await self.ai_engine.plugin_manager.registry.save_config()
                    return success
                return asyncio.run(async_disable())
            
            success = disable_plugin()
            if success:
                return jsonify({'success': True, 'message': f'Plugin {plugin_name} disabled'})
            else:
                return jsonify({'error': f'Failed to disable plugin {plugin_name}'}), 400
        
        @self.app.route('/api/plugins/<plugin_name>/config', methods=['GET', 'POST'])
        def api_plugin_config(plugin_name):
            """Get or update plugin configuration"""
            if not hasattr(self.ai_engine, 'plugin_manager') or not self.ai_engine.plugin_manager:
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
                        
                        def save_config():
                            async def async_save():
                                await self.ai_engine.plugin_manager.registry.save_config()
                            asyncio.run(async_save())
                        
                        save_config()
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
            if hasattr(self.ai_engine, 'plugin_manager') and self.ai_engine.plugin_manager:
                plugin_info = self.ai_engine.plugin_manager.get_plugin_info()
                self.socketio.emit('plugin_status', {'plugins': plugin_info})
            
            # Send VTS status on connect
            vts_status = self.live2d_streamer.get_stream_status()
            self.socketio.emit('vts_connection_update', vts_status)
            
            # Send plugin web UI info
            self.socketio.emit('plugin_webui_data', {
                'pages': self.plugin_pages,
                'assets': self.plugin_assets
            })
            
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
                        def get_dashboard_data():
                            async def async_get():
                                dashboard_data = await self.dashboard_manager.get_dashboard_metrics()
                                
                                # Add plugin metrics
                                if hasattr(self.ai_engine, 'plugin_manager') and self.ai_engine.plugin_manager:
                                    plugin_metrics = await self.ai_engine.plugin_manager.dispatch_dashboard_update()
                                    dashboard_data['plugin_metrics'] = plugin_metrics
                                
                                return dashboard_data
                            return asyncio.run(async_get())
                        
                        dashboard_data = get_dashboard_data()
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
            self.logger.info(f"Updating emotion to: {emotion}")
            
            def update_emotion_async():
                async def async_update():
                    await self.live2d_streamer.update_emotion(emotion)
                asyncio.run(async_update())
            
            thread = threading.Thread(target=update_emotion_async)
            thread.daemon = True
            thread.start()
            
            self.socketio.emit('emotion_updated', {'emotion': emotion}, broadcast=True)
        
        @self.socketio.on('request_dashboard_data')
        def handle_dashboard_request():
            def send_dashboard_data():
                async def async_send():
                    try:
                        dashboard_data = await self.dashboard_manager.get_dashboard_metrics()
                        
                        # Add plugin metrics
                        if hasattr(self.ai_engine, 'plugin_manager') and self.ai_engine.plugin_manager:
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
        
        # VTS Management Socket Events
        @self.socketio.on('get_vts_status')
        def handle_get_vts_status():
            """Send current VTS status to client"""
            vts_status = self.live2d_streamer.get_stream_status()
            self.socketio.emit('vts_status_update', vts_status)
        
        @self.socketio.on('start_vts_stream')
        def handle_start_vts_stream():
            """Start VTS streaming"""
            self.live2d_streamer.start_streaming()
            vts_status = self.live2d_streamer.get_stream_status()
            self.socketio.emit('vts_status_update', vts_status)
        
        @self.socketio.on('connect_to_vts')
        def handle_connect_to_vts():
            """Connect to VTube Studio"""
            def connect_async():
                async def async_connect():
                    success = await self.live2d_streamer.connect_to_vts()
                    vts_status = self.live2d_streamer.get_stream_status()
                    self.socketio.emit('vts_connection_update', vts_status)
                    if success:
                        self.socketio.emit('vts_connected', {'connected': True})
                    else:
                        self.socketio.emit('vts_error', {'error': 'Failed to connect to VTS'})
                asyncio.run(async_connect())
            
            thread = threading.Thread(target=connect_async)
            thread.daemon = True
            thread.start()
        
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
            if hasattr(self.ai_engine, 'plugin_manager') and self.ai_engine.plugin_manager:
                plugin_info = self.ai_engine.plugin_manager.get_plugin_info()
                self.socketio.emit('plugin_list', {'plugins': plugin_info})
        
        @self.socketio.on('enable_plugin')
        def handle_enable_plugin(data):
            """Enable a plugin via socket"""
            plugin_name = data.get('plugin_name')
            if not plugin_name or not hasattr(self.ai_engine, 'plugin_manager') or not self.ai_engine.plugin_manager:
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
            if not plugin_name or not hasattr(self.ai_engine, 'plugin_manager') or not self.ai_engine.plugin_manager:
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
            
            if not plugin_name or not config or not hasattr(self.ai_engine, 'plugin_manager') or not self.ai_engine.plugin_manager:
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
        
        # NEW: Plugin web UI socket events
        @self.socketio.on('get_plugin_webui')
        def handle_get_plugin_webui():
            """Send plugin web UI information to client"""
            self.socketio.emit('plugin_webui_data', {
                'pages': self.plugin_pages,
                'assets': self.plugin_assets
            })
        
        @self.socketio.on('reload_plugin_webui')
        def handle_reload_plugin_webui():
            """Reload plugin web UI routes and assets"""
            def reload_async():
                async def async_reload():
                    try:
                        # Clear existing plugin data
                        self.plugin_pages.clear()
                        self.plugin_assets = {'css': [], 'js': [], 'html_head': ''}
                        
                        # Re-register plugin routes
                        await self.register_plugin_routes()
                        
                        # Notify clients
                        self.socketio.emit('plugin_webui_reloaded', {
                            'pages': self.plugin_pages,
                            'assets': self.plugin_assets
                        }, broadcast=True)
                        
                        self.logger.info("✅ Plugin web UI reloaded")
                    except Exception as e:
                        self.logger.error(f"Error reloading plugin web UI: {e}")
                        self.socketio.emit('plugin_webui_error', {'error': str(e)})
                
                asyncio.run(async_reload())
            
            thread = threading.Thread(target=reload_async)
            thread.daemon = True
            thread.start()
    
    # MJPG Streaming Methods (unchanged from your original)
    def setup_mjpg_routes(self):
        """Setup MJPG streaming routes"""
        @self.app.route('/video_feed')
        def video_feed():
            """MJPG stream endpoint - raw camera feed"""
            return Response(
                self.generate_mjpg_frames(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
        
        @self.app.route('/video_feed_rgb')
        def video_feed_rgb():
            """MJPG stream endpoint with forced RGB conversion"""
            return Response(
                self.generate_mjpg_frames_rgb(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
        
        @self.app.route('/video_test')
        def video_test():
            """Test page for video feeds"""
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Video Feed Test</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        margin: 20px;
                        background: #1e293b;
                        color: white;
                    }
                    .container {
                        max-width: 1200px;
                        margin: 0 auto;
                    }
                    .video-grid {
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 20px;
                        margin-top: 20px;
                    }
                    .video-card {
                        background: #334155;
                        padding: 15px;
                        border-radius: 8px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    }
                    .video-card h3 {
                        margin-top: 0;
                        color: #fbbf24;
                    }
                    img {
                        width: 100%;
                        max-width: 640px;
                        border: 2px solid #4b5563;
                        border-radius: 4px;
                    }
                    .status {
                        padding: 10px;
                        margin: 10px 0;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                    .status.online {
                        background: #10b981;
                        color: white;
                    }
                    .status.offline {
                        background: #ef4444;
                        color: white;
                    }
                    .instructions {
                        background: #475569;
                        padding: 15px;
                        border-radius: 8px;
                        margin-top: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎥 Video Feed Test</h1>
                    <p>Testing different video streaming methods for color accuracy</p>
                    
                    <div class="video-grid">
                        <div class="video-card">
                            <h3>Raw Camera Feed</h3>
                            <div class="status" id="status1">Checking...</div>
                            <img src="/video_feed" id="feed1" onerror="document.getElementById('status1').className='status offline'; document.getElementById('status1').textContent='❌ Feed Error'" onload="document.getElementById('status1').className='status online'; document.getElementById('status1').textContent='✅ Feed Active'">
                            <p>Direct camera feed without processing</p>
                        </div>
                        
                        <div class="video-card">
                            <h3>RGB Converted Feed</h3>
                            <div class="status" id="status2">Checking...</div>
                            <img src="/video_feed_rgb" id="feed2" onerror="document.getElementById('status2').className='status offline'; document.getElementById('status2').textContent='❌ Feed Error'" onload="document.getElementById('status2').className='status online'; document.getElementById('status2').textContent='✅ Feed Active'">
                            <p>Feed with BGR→RGB conversion</p>
                        </div>
                    </div>
                    
                    <div class="instructions">
                        <h3>🔧 Testing Instructions:</h3>
                        <ul>
                            <li><strong>Raw Feed:</strong> Should show original camera colors (may be BGR)</li>
                            <li><strong>RGB Feed:</strong> Should show corrected colors</li>
                            <li>Compare both feeds to identify color issues</li>
                            <li>If both are wrong, try different conversion methods</li>
                        </ul>
                        
                        <h3>🎨 Color Space Tests:</h3>
                        <button onclick="testColorSpaces()">Run Color Space Tests</button>
                        <div id="colorTests"></div>
                    </div>
                </div>
                
                <script>
                    function testColorSpaces() {
                        const tests = document.getElementById('colorTests');
                        tests.innerHTML = '<p>Running color space analysis...</p>';
                        
                        // Test different color conversions
                        setTimeout(() => {
                            tests.innerHTML = `
                                <h4>Color Space Test Results:</h4>
                                <p>1. Check if red objects appear red in RGB feed</p>
                                <p>2. Check if blue objects appear blue in RGB feed</p>
                                <p>3. Compare skin tones between feeds</p>
                                <p><strong>Note:</strong> If colors are still wrong, the camera might be using a non-standard color space.</p>
                            `;
                        }, 1000);
                    }
                    
                    // Auto-refresh feeds every 30 seconds
                    setInterval(() => {
                        document.getElementById('feed1').src = '/video_feed?' + new Date().getTime();
                        document.getElementById('feed2').src = '/video_feed_rgb?' + new Date().getTime();
                    }, 30000);
                </script>
            </body>
            </html>
            '''
    
    def start_mjpg_frame_updater(self):
        """Start thread to continuously update MJPG frames from camera"""
        def frame_updater():
            self.logger.info("🔄 Starting MJPG frame updater thread")
            last_camera_state = False
            
            while True:
                try:
                    # Check if camera is available and streaming
                    camera_available = (self.live2d_streamer.cap and 
                                      self.live2d_streamer.camera_initialized and 
                                      self.live2d_streamer.is_streaming)
                    
                    # Log camera state changes
                    if camera_available != last_camera_state:
                        if camera_available:
                            self.logger.info("📹 Camera available for MJPG streaming")
                        else:
                            self.logger.warning("📹 Camera not available for MJPG streaming")
                        last_camera_state = camera_available
                    
                    if camera_available:
                        # Use the same camera instance as WebSocket stream
                        ret, frame = self.live2d_streamer.cap.read()
                        if ret and frame is not None:
                            with self.mjpg_frame_lock:
                                self.mjpg_frame = frame.copy()
                            self.mjpg_frame_available.set()
                        else:
                            self.logger.warning("📹 Failed to read frame from camera")
                            self.mjpg_frame_available.clear()
                    else:
                        # Camera not available, clear frame
                        with self.mjpg_frame_lock:
                            self.mjpg_frame = None
                        self.mjpg_frame_available.clear()
                    
                    time.sleep(0.033)  # ~30 FPS
                    
                except Exception as e:
                    self.logger.error(f"MJPG frame updater error: {e}")
                    self.mjpg_frame_available.clear()
                    time.sleep(1)
        
        thread = threading.Thread(target=frame_updater, daemon=True)
        thread.start()
    
    def generate_mjpg_frames(self):
        """Generate MJPG frames - raw camera feed"""
        self.logger.info("🎬 Starting MJPG stream (raw)")
        frame_count = 0
        consecutive_errors = 0
        
        while True:
            try:
                # Wait for frame to be available (with timeout)
                frame_ready = self.mjpg_frame_available.wait(timeout=1.0)
                
                if frame_ready:
                    with self.mjpg_frame_lock:
                        if self.mjpg_frame is not None:
                            frame = self.mjpg_frame.copy()
                        else:
                            frame = self._generate_placeholder_frame()
                else:
                    # No frame available, use placeholder
                    frame = self._generate_placeholder_frame()
                
                # Encode frame as JPEG
                success, jpeg = cv2.imencode('.jpg', frame, [
                    cv2.IMWRITE_JPEG_QUALITY, 80
                ])
                
                if success:
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + 
                          jpeg.tobytes() + b'\r\n')
                    frame_count += 1
                    consecutive_errors = 0
                    
                    # Log first few frames
                    if frame_count <= 3:
                        self.logger.info(f"📦 MJPG Frame {frame_count} sent")
                else:
                    self.logger.warning("Failed to encode MJPG frame")
                    consecutive_errors += 1
                
                # If too many errors, slow down
                sleep_time = 0.033  # ~30 FPS
                if consecutive_errors > 10:
                    sleep_time = 0.5  # Slow down on errors
                
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"MJPG stream error: {e}")
                consecutive_errors += 1
                time.sleep(0.5)
    
    def generate_mjpg_frames_rgb(self):
        """Generate MJPG frames with RGB conversion"""
        self.logger.info("🎬 Starting MJPG stream (RGB converted)")
        frame_count = 0
        consecutive_errors = 0
        
        while True:
            try:
                # Wait for frame to be available (with timeout)
                frame_ready = self.mjpg_frame_available.wait(timeout=1.0)
                
                if frame_ready:
                    with self.mjpg_frame_lock:
                        if self.mjpg_frame is not None:
                            frame = self.mjpg_frame.copy()
                        else:
                            frame = self._generate_placeholder_frame()
                else:
                    # No frame available, use placeholder
                    frame = self._generate_placeholder_frame()
                
                # Apply multiple color conversion attempts
                processed_frame = self._apply_color_corrections(frame)
                
                # Encode frame as JPEG
                success, jpeg = cv2.imencode('.jpg', processed_frame, [
                    cv2.IMWRITE_JPEG_QUALITY, 80
                ])
                
                if success:
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + 
                          jpeg.tobytes() + b'\r\n')
                    frame_count += 1
                    consecutive_errors = 0
                    
                    # Log first few frames
                    if frame_count <= 3:
                        self.logger.info(f"📦 MJPG RGB Frame {frame_count} sent")
                else:
                    self.logger.warning("Failed to encode MJPG RGB frame")
                    consecutive_errors += 1
                
                # If too many errors, slow down
                sleep_time = 0.033  # ~30 FPS
                if consecutive_errors > 10:
                    sleep_time = 0.5  # Slow down on errors
                
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"MJPG RGB stream error: {e}")
                consecutive_errors += 1
                time.sleep(0.5)
    
    def _apply_color_corrections(self, frame):
        """Apply multiple color correction methods"""
        if len(frame.shape) != 3 or frame.shape[2] != 3:
            return frame
        
        # Method 1: Standard BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Method 2: Check if we need manual channel swapping
        blue_mean = frame[:, :, 0].mean()
        green_mean = frame[:, :, 1].mean()
        red_mean = frame[:, :, 2].mean()
        
        self.logger.debug(f"Color means - B:{blue_mean:.1f} G:{green_mean:.1f} R:{red_mean:.1f}")
        
        # If blue channel is dominant, it's likely BGR format
        if blue_mean > red_mean + 20:
            self.logger.debug("Applying manual BGR→RGB conversion")
            frame_rgb = frame[:, :, [2, 1, 0]]  # Manual swap
        
        # Method 3: Try different color spaces if needed
        if blue_mean > green_mean + 30 and blue_mean > red_mean + 30:
            self.logger.debug("Trying alternative color space conversion")
            try:
                # Try HSV conversion and back
                frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                frame_rgb = cv2.cvtColor(frame_hsv, cv2.COLOR_HSV2RGB)
            except:
                pass
        
        return frame_rgb
    
    def _generate_placeholder_frame(self):
        """Generate a placeholder frame when no camera is available"""
        try:
            # Try using numpy if available
            import numpy as np
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = (50, 50, 150)  # Blue background
            
            # Add text
            cv2.putText(frame, "No Camera Feed", (150, 200), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(frame, "Check camera connection", (120, 250), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            return frame
            
        except ImportError:
            # Fallback without numpy - create a simple colored frame using OpenCV
            # Create a blank image using OpenCV
            frame = cv2.imread('')  # This will create an empty mat
            if frame is None:
                # If that fails, create a simple gradient
                height, width = 480, 640
                frame = cv2.applyColorMap(
                    cv2.resize(
                        cv2.imread('', cv2.IMREAD_GRAYSCALE) if cv2.imread('', cv2.IMREAD_GRAYSCALE) is not None 
                        else cv2.Mat(height, width, cv2.CV_8UC1, 128), 
                        (width, height)
                    ), 
                    cv2.COLORMAP_OCEAN
                )
            
            # Add text
            cv2.putText(frame, "No Camera - Numpy Missing", (100, 200), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, "Install: pip install numpy", (120, 250), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            return frame

    def run(self):
        # Register plugin routes before starting
        def register_routes_sync():
            asyncio.run(self.register_plugin_routes())
        
        # Run registration in thread to avoid blocking
        thread = threading.Thread(target=register_routes_sync)
        thread.daemon = True
        thread.start()
        thread.join(timeout=10)  # Wait up to 10 seconds for registration
        
        self.logger.info(f"Starting Enhanced WebUI on {self.host}:{self.port}")
        self.logger.info(f"✅ Plugin WebUI Support: {len(self.plugin_pages)} pages registered")
        self.logger.info("Features: Themes, Dashboard, Live2D Streaming, Plugin System, WebUI Support, Configuration Management, MJPG Streaming")
        self.socketio.run(self.app, host=self.host, port=self.port, debug=False, allow_unsafe_werkzeug=True)