// Service status monitoring and management
class ServiceManager {
    constructor(app) {
        this.app = app;
        this.services = new Map();
        this.initializeServices();
        this.startMonitoring();
    }
    
    initializeServices() {
        // Define service configurations
        this.services.set('ollama', {
            name: 'Ollama',
            icon: 'fas fa-brain',
            endpoint: '/api/status',
            checkInterval: 30000,
            enabled: true
        });
        
        this.services.set('discord', {
            name: 'Discord Bot',
            icon: 'fab fa-discord',
            endpoint: '/api/status',
            checkInterval: 30000,
            enabled: true
        });
        
        this.services.set('vts', {
            name: 'VTube Studio',
            icon: 'fas fa-desktop',
            endpoint: '/api/status',
            checkInterval: 30000,
            enabled: true
        });
        
        this.services.set('plugins', {
            name: 'Plugin System',
            icon: 'fas fa-puzzle-piece',
            endpoint: '/api/status',
            checkInterval: 30000,
            enabled: true
        });
        
        this.createServiceCards();
    }
    
    createServiceCards() {
        const servicesContainer = document.querySelector('.service-status-grid');
        if (!servicesContainer) return;
        
        servicesContainer.innerHTML = '';
        
        this.services.forEach((serviceConfig, serviceId) => {
            const card = this.createServiceCard(serviceId, serviceConfig);
            servicesContainer.appendChild(card);
        });
    }
    
    createServiceCard(serviceId, serviceConfig) {
        const card = document.createElement('div');
        card.className = 'service-card';
        card.dataset.service = serviceId;
        
        card.innerHTML = `
            <div class="service-header">
                <div class="service-name">
                    <i class="${serviceConfig.icon}"></i>
                    ${serviceConfig.name}
                </div>
                <div class="service-status">
                    <span class="status-indicator status-offline"></span>
                    <span>Offline</span>
                </div>
            </div>
            <div class="service-details">Checking status...</div>
            <div class="service-controls" style="margin-top: 8px; display: flex; gap: 8px;">
                <label style="display: flex; align-items: center; gap: 4px; font-size: 0.8rem;">
                    <input type="checkbox" class="service-toggle" data-service="${serviceId}" ${serviceConfig.enabled ? 'checked' : ''}>
                    Enable
                </label>
                <button class="test-connection" data-service="${serviceId}" style="padding: 2px 8px; font-size: 0.8rem; border: 1px solid var(--primary-color); background: transparent; color: var(--primary-color); border-radius: 4px;">
                    Test
                </button>
            </div>
        `;
        
        return card;
    }
    
    startMonitoring() {
        // Initial check
        this.checkAllServices();
        
        // Set up periodic checking
        this.monitoringInterval = setInterval(() => {
            this.checkAllServices();
        }, 30000);
    }
    
    async checkAllServices() {
        const promises = Array.from(this.services.keys()).map(serviceId => 
            this.checkService(serviceId)
        );
        
        await Promise.allSettled(promises);
    }
    
    async checkService(serviceId) {
        const service = this.services.get(serviceId);
        if (!service || !service.enabled) return;
        
        try {
            const response = await fetch(service.endpoint);
            const data = await response.json();
            
            this.updateServiceStatus(serviceId, {
                online: this.determineServiceStatus(serviceId, data),
                details: this.getServiceDetails(serviceId, data),
                lastChecked: new Date().toISOString()
            });
            
        } catch (error) {
            console.error(`Error checking service ${serviceId}:`, error);
            this.updateServiceStatus(serviceId, {
                online: false,
                details: 'Connection failed',
                lastChecked: new Date().toISOString()
            });
        }
    }
    
    determineServiceStatus(serviceId, statusData) {
        switch(serviceId) {
            case 'ollama':
                return statusData.features?.ai_engine || false;
            case 'discord':
                return statusData.config?.discord_enabled || false;
            case 'vts':
                return statusData.config?.vts_enabled || false;
            case 'plugins':
                return statusData.plugins ? true : false;
            default:
                return false;
        }
    }
    
    getServiceDetails(serviceId, statusData) {
        switch(serviceId) {
            case 'ollama':
                return `Model: ${statusData.config?.ollama_model || 'Unknown'}`;
            case 'discord':
                return statusData.config?.discord_enabled ? 'Bot connected' : 'Bot disabled';
            case 'vts':
                return statusData.config?.vts_enabled ? 'VTS connected' : 'VTS disabled';
            case 'plugins':
                return `Enabled: ${statusData.plugins?.enabled || 0}/${statusData.plugins?.loaded || 0}`;
            default:
                return 'Status unknown';
        }
    }
    
    updateServiceStatus(serviceId, status) {
        const card = document.querySelector(`[data-service="${serviceId}"]`);
        if (!card) return;
        
        const statusElement = card.querySelector('.service-status');
        const detailsElement = card.querySelector('.service-details');
        const indicator = card.querySelector('.status-indicator');
        
        if (statusElement && detailsElement && indicator) {
            // Update visual status
            indicator.className = 'status-indicator';
            indicator.classList.add(status.online ? 'status-online' : 'status-offline');
            
            // Update status text
            const statusText = statusElement.querySelector('span:last-child');
            if (statusText) {
                statusText.textContent = status.online ? 'Online' : 'Offline';
            }
            
            // Update details
            detailsElement.textContent = status.details;
        }
        
        // Store service status
        if (this.services.has(serviceId)) {
            this.services.get(serviceId).lastStatus = status;
        }
    }
    
    async toggleService(serviceId, enabled) {
        const service = this.services.get(serviceId);
        if (!service) return;
        
        service.enabled = enabled;
        
        try {
            // Make API call to enable/disable service
            const response = await fetch(`/api/config/services/${serviceId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ enabled })
            });
            
            if (response.ok) {
                this.updateServiceStatus(serviceId, {
                    online: enabled,
                    details: enabled ? 'Service enabled' : 'Service disabled',
                    lastChecked: new Date().toISOString()
                });
            }
        } catch (error) {
            console.error(`Error toggling service ${serviceId}:`, error);
        }
    }
    
    async testServiceConnection(serviceId) {
        const testButton = document.querySelector(`[data-service="${serviceId}"] .test-connection`);
        if (testButton) {
            testButton.disabled = true;
            testButton.textContent = 'Testing...';
        }
        
        await this.checkService(serviceId);
        
        if (testButton) {
            testButton.disabled = false;
            testButton.textContent = 'Test';
        }
    }
    
    getServiceStatus(serviceId) {
        return this.services.get(serviceId)?.lastStatus || { online: false, details: 'Unknown' };
    }
    
    getAllServicesStatus() {
        const status = {};
        this.services.forEach((service, serviceId) => {
            status[serviceId] = this.getServiceStatus(serviceId);
        });
        return status;
    }
    
    stopMonitoring() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
        }
    }
}

// Export for use in main app
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ServiceManager;
}