// Test WebUI Plugin JavaScript
class TestWebUIPlugin {
    constructor() {
        this.metricsInterval = null;
        this.initialized = false;
    }

    init() {
        if (this.initialized) return;
        
        console.log('🔧 Test WebUI Plugin initializing...');
        
        // Inject custom UI elements
        this.injectDashboardWidget();
        
        // Start metrics updates if on test webui page
        if (window.location.pathname.includes('/test-webui')) {
            this.startMetricsUpdates();
        }
        
        this.initialized = true;
        console.log('✅ Test WebUI Plugin initialized');
    }

    injectDashboardWidget() {
        // Look for dashboard container to inject our widget
        const dashboard = document.querySelector('.dashboard-container, [class*="dashboard"]');
        if (dashboard) {
            const widget = this.createDashboardWidget();
            dashboard.prepend(widget);
        }
    }

    createDashboardWidget() {
        const widget = document.createElement('div');
        widget.className = 'test-webui-dashboard-widget';
        widget.innerHTML = `
            <div class="test-webui-container">
                <h4>🧪 Test WebUI Plugin</h4>
                <div class="test-webui-status connected">
                    ✅ Plugin Active
                </div>
                <button onclick="testWebUI.showTestNotification()" class="btn btn-sm btn-outline-primary">
                    Test Notification
                </button>
            </div>
        `;
        return widget;
    }

    startMetricsUpdates() {
        // Update metrics every 3 seconds
        this.metricsInterval = setInterval(() => {
            this.fetchMetrics();
        }, 3000);

        // Set up message form handler
        const messageForm = document.getElementById('test-webui-message-form');
        if (messageForm) {
            messageForm.addEventListener('submit', (e) => this.handleMessageSubmit(e));
        }
    }

    async fetchMetrics() {
        try {
            const response = await fetch('/test-webui/api/metrics');
            const data = await response.json();
            
            if (data.success) {
                this.updateMetricsDisplay(data.metrics);
            }
        } catch (error) {
            console.error('Failed to fetch metrics:', error);
        }
    }

    updateMetricsDisplay(metrics) {
        // Update metrics cards
        const elements = {
            'requests_served': document.getElementById('metric-requests'),
            'messages_processed': document.getElementById('metric-messages'),
            'uptime': document.getElementById('metric-uptime'),
            'settings_changed': document.getElementById('metric-settings')
        };

        for (const [key, element] of Object.entries(elements)) {
            if (element && metrics[key] !== undefined) {
                if (key === 'uptime') {
                    element.textContent = `${metrics[key].toFixed(1)}s`;
                } else {
                    element.textContent = metrics[key];
                }
            }
        }
    }

    async handleMessageSubmit(event) {
        event.preventDefault();
        
        const messageInput = document.getElementById('test-webui-message-input');
        const statusDiv = document.getElementById('test-webui-status');
        
        if (!messageInput.value.trim()) return;

        try {
            const response = await fetch('/test-webui/api/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: messageInput.value
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showStatus('Message sent successfully!', 'success');
                messageInput.value = '';
                this.addMessageToDisplay(messageInput.value);
            } else {
                this.showStatus('Failed to send message: ' + data.error, 'error');
            }
        } catch (error) {
            this.showStatus('Error sending message: ' + error.message, 'error');
        }
    }

    addMessageToDisplay(message) {
        const messageList = document.getElementById('test-webui-message-list');
        if (messageList) {
            const messageItem = document.createElement('div');
            messageItem.className = 'test-webui-message-item';
            messageItem.innerHTML = `
                <strong>User:</strong> ${message}
                <div class="test-webui-message-time">${new Date().toLocaleTimeString()}</div>
            `;
            messageList.appendChild(messageItem);
            messageList.scrollTop = messageList.scrollHeight;
        }
    }

    showStatus(message, type = 'info') {
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

    showTestNotification() {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('Test WebUI Plugin', {
                body: 'This is a test notification from the WebUI plugin!',
                icon: '/test-webui-static/images/icon.png'
            });
        } else {
            alert('Test notification: WebUI Plugin is working!');
        }
    }

    destroy() {
        if (this.metricsInterval) {
            clearInterval(this.metricsInterval);
        }
        this.initialized = false;
    }
}

// Initialize plugin when DOM is loaded
const testWebUI = new TestWebUIPlugin();
document.addEventListener('DOMContentLoaded', () => testWebUI.init());