// Tab management system
class TabManager {
    constructor(app) {
        this.app = app;
        this.tabs = new Map();
        this.initializeTabs();
    }
    
    initializeTabs() {
        // Define tab structure
        this.tabs.set('main', {
            name: 'Main',
            icon: 'fas fa-comments',
            component: 'chat-interface',
            priority: 1
        });
        
        this.tabs.set('analytics', {
            name: 'Analytics & Settings',
            icon: 'fas fa-chart-bar',
            component: 'analytics-settings',
            priority: 2
        });
        
        this.tabs.set('appearance', {
            name: 'Appearance',
            icon: 'fas fa-palette',
            component: 'appearance-tab',
            priority: 3
        });
        
        this.createTabNavigation();
    }
    
    createTabNavigation() {
        const tabContainer = document.querySelector('.tab-navigation');
        if (!tabContainer) return;
        
        // Clear existing tabs
        tabContainer.innerHTML = '';
        
        // Create tab buttons in priority order
        const sortedTabs = Array.from(this.tabs.entries())
            .sort((a, b) => a[1].priority - b[1].priority);
        
        sortedTabs.forEach(([tabId, tabConfig]) => {
            const tabButton = this.createTabButton(tabId, tabConfig);
            tabContainer.appendChild(tabButton);
        });
    }
    
    createTabButton(tabId, tabConfig) {
        const button = document.createElement('button');
        button.className = 'tab-button';
        button.dataset.tab = tabId;
        button.innerHTML = `
            <i class="${tabConfig.icon}"></i>
            <span>${tabConfig.name}</span>
        `;
        
        button.addEventListener('click', () => {
            this.switchToTab(tabId);
        });
        
        return button;
    }
    
    switchToTab(tabId) {
        if (!this.tabs.has(tabId)) {
            console.warn(`Tab ${tabId} not found`);
            return;
        }
        
        // Hide all tab contents
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // Remove active class from all buttons
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active');
        });
        
        // Show target tab
        const targetTab = document.getElementById(`${tabId}-tab`);
        const targetButton = document.querySelector(`[data-tab="${tabId}"]`);
        
        if (targetTab && targetButton) {
            targetTab.classList.add('active');
            targetButton.classList.add('active');
            
            // Trigger tab-specific initialization
            this.onTabActivated(tabId);
        }
    }
    
    onTabActivated(tabId) {
        const tabConfig = this.tabs.get(tabId);
        if (!tabConfig) return;
        
        switch(tabId) {
            case 'main':
                this.initializeMainTab();
                break;
            case 'analytics':
                this.initializeAnalyticsTab();
                break;
            case 'appearance':
                this.initializeAppearanceTab();
                break;
        }
        
        // Update app state
        this.app.currentTab = tabId;
    }
    
    initializeMainTab() {
        // Focus message input
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            setTimeout(() => messageInput.focus(), 100);
        }
        
        // Ensure Live2D is visible and active
        this.ensureLive2DActive();
    }
    
    initializeAnalyticsTab() {
        // Load fresh analytics data
        this.app.loadAnalyticsData();
        
        // Start real-time updates if needed
        this.startAnalyticsUpdates();
    }
    
    initializeAppearanceTab() {
        // Load theme gallery if dynamic
        this.app.loadThemeGallery();
    }
    
    ensureLive2DActive() {
        // Ensure Live2D stream is running when on main tab
        if (window.live2dStreamer) {
            // Implementation depends on your Live2D setup
        }
    }
    
    startAnalyticsUpdates() {
        // Start periodic updates for analytics tab
        this.analyticsInterval = setInterval(() => {
            if (this.app.currentTab === 'analytics') {
                this.app.loadAnalyticsData();
            }
        }, 10000); // Update every 10 seconds when tab is active
    }
    
    stopAnalyticsUpdates() {
        if (this.analyticsInterval) {
            clearInterval(this.analyticsInterval);
        }
    }
    
    // Method to add dynamic tabs (for plugins, etc.)
    addTab(tabId, tabConfig) {
        this.tabs.set(tabId, tabConfig);
        this.createTabNavigation();
    }
    
    removeTab(tabId) {
        this.tabs.delete(tabId);
        this.createTabNavigation();
    }
}

// Export for use in main app
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TabManager;
}