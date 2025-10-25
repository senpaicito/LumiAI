from src.core.plugin_system.plugin_base import BasePlugin
from typing import Any, Dict, List, Optional
from pathlib import Path
import json
import time
import asyncio

class TestWebUIPlugin(BasePlugin):
    """Test WebUI Plugin for Lumi Companion App"""
    
    def __init__(self):
        super().__init__(
            name="test_webui",
            version="1.0.0",
            description="A test plugin for WebUI integration testing"
        )
        self.metrics = {
            'requests_served': 0,
            'messages_processed': 0,
            'uptime': 0,
            'last_update': time.time()
        }
        self.custom_data = {
            'messages': [],
            'settings_changed': 0
        }
    
    async def initialize(self) -> bool:
        """Initialize the test WebUI plugin"""
        try:
            self.logger.info("🔄 Initializing Test WebUI Plugin...")
            
            # Load saved data
            self.custom_data = self.load_plugin_data('custom_data.json', self.custom_data)
            self.metrics = self.load_plugin_data('metrics.json', self.metrics)
            
            # Start background tasks if needed
            if self.get_config_value('real_time_updates', False):
                asyncio.create_task(self._background_updater())
            
            self.logger.info("✅ Test WebUI Plugin initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Test WebUI Plugin: {e}")
            return False
    
    async def unload(self) -> bool:
        """Cleanup and unload the plugin"""
        try:
            # Save plugin data
            self.save_plugin_data(self.custom_data, 'custom_data.json')
            self.save_plugin_data(self.metrics, 'metrics.json')
            
            self.logger.info("✅ Test WebUI Plugin unloaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error unloading Test WebUI Plugin: {e}")
            return False
    
    async def _background_updater(self):
        """Background task for real-time updates"""
        while self.enabled:
            await asyncio.sleep(5)
            self.metrics['uptime'] = time.time() - self.metrics['last_update']
    
    # Web UI Integration Methods
    
    async def get_web_routes(self) -> List[Dict]:
        """Define Flask routes for this plugin"""
        return [
            {
                'name': 'dashboard',
                'path': '/',
                'methods': ['GET'],
                'endpoint': 'test_webui_dashboard',
                'view_func': self._handle_dashboard_request
            },
            {
                'name': 'metrics',
                'path': '/api/metrics',
                'methods': ['GET'],
                'endpoint': 'test_webui_metrics',
                'view_func': self._handle_metrics_request
            },
            {
                'name': 'message',
                'path': '/api/message',
                'methods': ['POST'],
                'endpoint': 'test_webui_message',
                'view_func': self._handle_message_request
            },
            {
                'name': 'settings',
                'path': '/api/settings',
                'methods': ['GET', 'POST'],
                'endpoint': 'test_webui_settings',
                'view_func': self._handle_settings_request
            },
            {
                'name': 'health',
                'path': '/api/health',
                'methods': ['GET'],
                'endpoint': 'test_webui_health',
                'view_func': self._handle_health_request
            },
            {
                'name': 'static_css',
                'path': '/static/css/<filename>',
                'methods': ['GET'],
                'endpoint': 'test_webui_static_css',
                'view_func': self._handle_static_css
            },
            {
                'name': 'static_js',
                'path': '/static/js/<filename>',
                'methods': ['GET'],
                'endpoint': 'test_webui_static_js',
                'view_func': self._handle_static_js
            }
        ]
    
    async def get_static_files(self) -> Dict[str, Path]:
        """Serve static files for this plugin - RETURN EMPTY DICT TO AVOID ERROR"""
        # Return empty dict since we're handling static files via routes
        return {}
    
    async def get_template_variables(self) -> Dict:
        """Inject variables into template context"""
        return {
            'test_webui_plugin': {
                'name': self.name,
                'version': self.version,
                'enabled': self.enabled,
                'custom_message': self.get_config_value('custom_message', 'Hello!')
            }
        }
    
    async def get_ui_assets(self) -> Dict:
        """Inject CSS/JS assets into main UI"""
        return {
            'css': [],
            'js': [],
            'html_head': '''
            <!-- Test WebUI Plugin Header Injection -->
            <meta name="test-webui-version" content="1.0.0">
            '''
        }
    
    async def get_plugin_pages(self) -> List[Dict]:
        """Add plugin pages to navigation"""
        return [
            {
                'name': 'Test WebUI',
                'url': '/plugin/test_webui/',
                'icon': 'fa-solid fa-vial',
                'category': 'plugins',
                'order': 10
            }
        ]
    
    # Flask Route Handlers
    
    def _handle_dashboard_request(self):
        """Handle dashboard page request"""
        from flask import render_template_string
        
        html_template = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test WebUI Plugin - Lumi Companion</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <style>
                .test-webui-container { padding: 20px; background: #f5f5f5; border-radius: 8px; margin: 10px 0; }
                .test-webui-metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
                .test-webui-metric-card { background: white; padding: 15px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
                .test-webui-metric-value { font-size: 24px; font-weight: bold; color: #2196F3; }
                .test-webui-metric-label { font-size: 14px; color: #666; margin-top: 5px; }
                .test-webui-message-form { background: white; padding: 20px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .test-webui-status { padding: 10px; border-radius: 4px; margin: 10px 0; text-align: center; }
                .test-webui-status.success { background: #E8F5E8; color: #2E7D32; }
                .test-webui-status.error { background: #FFEBEE; color: #C62828; }
            </style>
        </head>
        <body>
            <div class="container-fluid">
                <div class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <h2><i class="fas fa-vial"></i> Test WebUI Plugin</h2>
                                <p class="text-muted">Version {{ version }} - Testing WebUI Integration</p>
                            </div>
                            <div class="card-body">
                                <!-- Metrics Display -->
                                <div class="test-webui-metrics">
                                    <div class="test-webui-metric-card">
                                        <div class="test-webui-metric-value" id="metric-requests">{{ metrics.requests_served }}</div>
                                        <div class="test-webui-metric-label">Requests Served</div>
                                    </div>
                                    <div class="test-webui-metric-card">
                                        <div class="test-webui-metric-value" id="metric-messages">{{ metrics.messages_processed }}</div>
                                        <div class="test-webui-metric-label">Messages Processed</div>
                                    </div>
                                    <div class="test-webui-metric-card">
                                        <div class="test-webui-metric-value" id="metric-uptime">{{ "%.1f"|format(metrics.uptime) }}s</div>
                                        <div class="test-webui-metric-label">Uptime</div>
                                    </div>
                                    <div class="test-webui-metric-card">
                                        <div class="test-webui-metric-value" id="metric-settings">{{ custom_data.settings_changed }}</div>
                                        <div class="test-webui-metric-label">Settings Changed</div>
                                    </div>
                                </div>

                                <!-- Message Form -->
                                <div class="test-webui-message-form">
                                    <h5>Send Test Message</h5>
                                    <form id="test-webui-message-form">
                                        <div class="input-group">
                                            <input type="text" 
                                                   id="test-webui-message-input"
                                                   class="form-control" 
                                                   placeholder="Enter a test message..." 
                                                   required>
                                            <button type="submit" class="btn btn-primary">Send</button>
                                        </div>
                                    </form>
                                    <div id="test-webui-status" class="test-webui-status"></div>
                                </div>

                                <!-- Plugin Information -->
                                <div class="mt-4">
                                    <h5>Plugin Information</h5>
                                    <div class="row">
                                        <div class="col-md-6">
                                            <ul class="list-group">
                                                <li class="list-group-item">
                                                    <strong>Name:</strong> {{ name }}
                                                </li>
                                                <li class="list-group-item">
                                                    <strong>Version:</strong> {{ version }}
                                                </li>
                                                <li class="list-group-item">
                                                    <strong>Status:</strong> 
                                                    <span class="badge bg-success">Active</span>
                                                </li>
                                            </ul>
                                        </div>
                                        <div class="col-md-6">
                                            <ul class="list-group">
                                                <li class="list-group-item">
                                                    <strong>Theme:</strong> {{ config.theme }}
                                                </li>
                                                <li class="list-group-item">
                                                    <strong>Update Interval:</strong> {{ config.update_interval }}ms
                                                </li>
                                                <li class="list-group-item">
                                                    <strong>Notifications:</strong> 
                                                    {% if config.enable_notifications %}
                                                        <span class="badge bg-success">Enabled</span>
                                                    {% else %}
                                                        <span class="badge bg-secondary">Disabled</span>
                                                    {% endif %}
                                                </li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>

                                <!-- Test Buttons -->
                                <div class="mt-4">
                                    <h5>Test Actions</h5>
                                    <div class="btn-group">
                                        <button class="btn btn-outline-primary" onclick="testWebUI.fetchMetrics()">
                                            <i class="fas fa-sync-alt"></i> Refresh Metrics
                                        </button>
                                        <button class="btn btn-outline-success" onclick="testWebUI.testHealth()">
                                            <i class="fas fa-heartbeat"></i> Test Health
                                        </button>
                                        <button class="btn btn-outline-info" onclick="testWebUI.testSettings()">
                                            <i class="fas fa-cog"></i> Test Settings
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                class TestWebUIPlugin {
                    constructor() {
                        this.baseUrl = '/plugin/test_webui';
                    }

                    async fetchMetrics() {
                        try {
                            const response = await fetch(this.baseUrl + '/api/metrics');
                            const data = await response.json();
                            
                            if (data.success) {
                                document.getElementById('metric-requests').textContent = data.metrics.requests_served;
                                document.getElementById('metric-messages').textContent = data.metrics.messages_processed;
                                document.getElementById('metric-uptime').textContent = data.metrics.uptime.toFixed(1) + 's';
                                document.getElementById('metric-settings').textContent = data.metrics.settings_changed;
                                this.showStatus('Metrics updated!', 'success');
                            }
                        } catch (error) {
                            this.showStatus('Failed to fetch metrics: ' + error, 'error');
                        }
                    }

                    async testHealth() {
                        try {
                            const response = await fetch(this.baseUrl + '/api/health');
                            const data = await response.json();
                            this.showStatus('Health: ' + data.status, 'success');
                        } catch (error) {
                            this.showStatus('Health check failed: ' + error, 'error');
                        }
                    }

                    async testSettings() {
                        try {
                            const response = await fetch(this.baseUrl + '/api/settings');
                            const data = await response.json();
                            this.showStatus('Settings loaded successfully!', 'success');
                            console.log('Plugin settings:', data.settings);
                        } catch (error) {
                            this.showStatus('Settings load failed: ' + error, 'error');
                        }
                    }

                    showStatus(message, type = 'success') {
                        const statusDiv = document.getElementById('test-webui-status');
                        if (statusDiv) {
                            statusDiv.textContent = message;
                            statusDiv.className = `test-webui-status ${type}`;
                            setTimeout(() => {
                                statusDiv.textContent = '';
                                statusDiv.className = 'test-webui-status';
                            }, 3000);
                        }
                    }
                }

                // Initialize when page loads
                const testWebUI = new TestWebUIPlugin();
                
                // Set up message form
                document.getElementById('test-webui-message-form').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const input = document.getElementById('test-webui-message-input');
                    const message = input.value.trim();
                    
                    if (!message) return;

                    try {
                        const response = await fetch(testWebUI.baseUrl + '/api/message', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ message: message })
                        });

                        const data = await response.json();
                        
                        if (data.success) {
                            testWebUI.showStatus('Message sent successfully!', 'success');
                            input.value = '';
                            testWebUI.fetchMetrics(); // Refresh metrics
                        } else {
                            testWebUI.showStatus('Failed to send message: ' + data.error, 'error');
                        }
                    } catch (error) {
                        testWebUI.showStatus('Error sending message: ' + error.message, 'error');
                    }
                });

                // Auto-refresh metrics every 5 seconds
                setInterval(() => testWebUI.fetchMetrics(), 5000);
            </script>
        </body>
        </html>
        '''
        
        return render_template_string(html_template, 
            name=self.name,
            version=self.version,
            metrics=self.metrics,
            custom_data=self.custom_data,
            config=self.config
        )
    
    def _handle_metrics_request(self):
        """Handle metrics API request"""
        from flask import jsonify
        
        # Update metrics
        self.metrics['requests_served'] += 1
        self.metrics['uptime'] = time.time() - self.metrics['last_update']
        
        return jsonify({
            'success': True,
            'metrics': self.metrics,
            'timestamp': time.time()
        })
    
    def _handle_message_request(self):
        """Handle message API request"""
        from flask import jsonify, request
        
        try:
            data = request.get_json()
            message = data.get('message', '').strip()
            
            if message:
                self.custom_data['messages'].append({
                    'text': message,
                    'timestamp': time.time(),
                    'type': 'user'
                })
                
                # Keep only last 50 messages
                self.custom_data['messages'] = self.custom_data['messages'][-50:]
                
                self.metrics['messages_processed'] += 1
                
                return jsonify({
                    'success': True,
                    'message': 'Message received',
                    'total_messages': len(self.custom_data['messages'])
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'No message provided'
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    def _handle_settings_request(self):
        """Handle settings API request"""
        from flask import jsonify, request
        
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'settings': self.config,
                'plugin_info': {
                    'name': self.name,
                    'version': self.version,
                    'description': self.description
                }
            })
        
        elif request.method == 'POST':
            try:
                data = request.get_json()
                
                # Update config (in a real plugin, you'd validate this)
                for key, value in data.items():
                    if key in self.config:
                        self.config[key] = value
                
                self.custom_data['settings_changed'] += 1
                
                return jsonify({
                    'success': True,
                    'message': 'Settings updated',
                    'settings': self.config
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def _handle_health_request(self):
        """Handle health check request"""
        from flask import jsonify
        
        return jsonify({
            'status': 'healthy',
            'plugin': self.name,
            'version': self.version,
            'enabled': self.enabled,
            'timestamp': time.time()
        })
    
    def _handle_static_css(self, filename):
        """Handle CSS static files"""
        from flask import send_from_directory
        static_path = Path(__file__).parent / "static" / "css"
        return send_from_directory(str(static_path), filename)
    
    def _handle_static_js(self, filename):
        """Handle JS static files"""
        from flask import send_from_directory
        static_path = Path(__file__).parent / "static" / "js"
        return send_from_directory(str(static_path), filename)
    
    # Plugin Event Handlers
    
    async def on_message_received(self, message: str, message_type: str = "user") -> Optional[str]:
        """Process incoming messages"""
        if self.enabled and message_type == "user":
            self.metrics['messages_processed'] += 1
            
            # Example: Add a prefix if the message contains "test"
            if "test" in message.lower():
                return f"[TestPlugin] {message}"
        
        return None
    
    async def on_dashboard_update(self) -> Optional[Dict]:
        """Provide metrics for the main dashboard"""
        if not self.enabled:
            return None
            
        return {
            'title': 'Test WebUI Plugin',
            'type': 'metrics',
            'data': {
                'Requests Served': self.metrics['requests_served'],
                'Messages Processed': self.metrics['messages_processed'],
                'Uptime': f"{self.metrics['uptime']:.1f}s",
                'Settings Changed': self.custom_data['settings_changed']
            },
            'priority': 10
        }