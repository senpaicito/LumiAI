// Mobile-specific enhancements
class MobileEnhancements {
    constructor(app) {
        this.app = app;
        this.setupMobileOptimizations();
    }
    
    setupMobileOptimizations() {
        this.preventZoomOnInput();
        this.enhanceTouchInteractions();
        this.setupViewportManagement();
        this.optimizePerformance();
    }
    
    preventZoomOnInput() {
        // Prevent zoom on focus for inputs on iOS
        const inputs = document.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('focus', () => {
                document.body.style.fontSize = '16px';
            });
            input.addEventListener('blur', () => {
                document.body.style.fontSize = '';
            });
        });
    }
    
    enhanceTouchInteractions() {
        // Add touch feedback
        const touchElements = document.querySelectorAll('button, .tab-button, .theme-card, .service-card');
        touchElements.forEach(element => {
            element.addEventListener('touchstart', () => {
                element.style.transform = 'scale(0.98)';
            });
            
            element.addEventListener('touchend', () => {
                element.style.transform = '';
            });
        });
        
        // Improved scrolling
        this.setupMomentumScrolling();
    }
    
    setupMomentumScrolling() {
        // Add momentum scrolling for better touch experience
        const scrollElements = document.querySelectorAll('.chat-messages, .analytics-panel, .appearance-tab');
        scrollElements.forEach(element => {
            element.style.webkitOverflowScrolling = 'touch';
        });
    }
    
    setupViewportManagement() {
        // Handle viewport height for mobile browsers
        this.setViewportHeight();
        window.addEventListener('resize', this.debounce(() => this.setViewportHeight(), 250));
        window.addEventListener('orientationchange', () => {
            setTimeout(() => this.setViewportHeight(), 100);
        });
    }
    
    setViewportHeight() {
        // Use dvh for dynamic viewport height
        document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`);
    }
    
    optimizePerformance() {
        // Lazy load non-critical components
        this.lazyLoadComponents();
        
        // Reduce animations if device is slow
        if (this.isLowPerformanceDevice()) {
            this.reduceAnimations();
        }
    }
    
    lazyLoadComponents() {
        // Lazy load analytics charts when tab is activated
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Load heavy components here
                    observer.unobserve(entry.target);
                }
            });
        });
        
        const analyticsTab = document.getElementById('analytics-tab');
        if (analyticsTab) {
            observer.observe(analyticsTab);
        }
    }
    
    isLowPerformanceDevice() {
        // Simple performance detection
        return navigator.hardwareConcurrency <= 4 || 
               !('ontouchstart' in window) || // No touch support might indicate older device
               window.innerWidth <= 320; // Very small screen
    }
    
    reduceAnimations() {
        document.body.classList.add('reduced-motion');
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Mobile-specific gesture handling
class TouchGestures {
    constructor(app) {
        this.app = app;
        this.setupGestureHandlers();
    }
    
    setupGestureHandlers() {
        this.setupSwipeNavigation();
        this.setupPullToRefresh();
    }
    
    setupSwipeNavigation() {
        const tabs = ['main', 'analytics', 'appearance'];
        let startX = 0;
        let currentX = 0;
        
        document.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
        }, { passive: true });
        
        document.addEventListener('touchmove', (e) => {
            currentX = e.touches[0].clientX;
        }, { passive: true });
        
        document.addEventListener('touchend', () => {
            const diff = startX - currentX;
            const minSwipeDistance = 60; // pixels
            
            if (Math.abs(diff) > minSwipeDistance) {
                if (diff > 0 && this.canSwipeLeft()) {
                    this.swipeToNextTab();
                } else if (diff < 0 && this.canSwipeRight()) {
                    this.swipeToPreviousTab();
                }
            }
        });
    }
    
    canSwipeLeft() {
        const tabs = ['main', 'analytics', 'appearance'];
        return tabs.indexOf(this.app.currentTab) < tabs.length - 1;
    }
    
    canSwipeRight() {
        const tabs = ['main', 'analytics', 'appearance'];
        return tabs.indexOf(this.app.currentTab) > 0;
    }
    
    swipeToNextTab() {
        const tabs = ['main', 'analytics', 'appearance'];
        const currentIndex = tabs.indexOf(this.app.currentTab);
        if (currentIndex < tabs.length - 1) {
            this.app.switchTab(tabs[currentIndex + 1]);
        }
    }
    
    swipeToPreviousTab() {
        const tabs = ['main', 'analytics', 'appearance'];
        const currentIndex = tabs.indexOf(this.app.currentTab);
        if (currentIndex > 0) {
            this.app.switchTab(tabs[currentIndex - 1]);
        }
    }
    
    setupPullToRefresh() {
        // Simple pull-to-refresh for analytics tab
        let startY = 0;
        let currentY = 0;
        const analyticsPanel = document.querySelector('.analytics-panel');
        
        if (!analyticsPanel) return;
        
        analyticsPanel.addEventListener('touchstart', (e) => {
            if (analyticsPanel.scrollTop === 0) {
                startY = e.touches[0].clientY;
            }
        }, { passive: true });
        
        analyticsPanel.addEventListener('touchmove', (e) => {
            if (analyticsPanel.scrollTop === 0 && startY > 0) {
                currentY = e.touches[0].clientY;
                const pullDistance = currentY - startY;
                
                if (pullDistance > 0) {
                    e.preventDefault();
                    this.showPullIndicator(pullDistance);
                }
            }
        });
        
        analyticsPanel.addEventListener('touchend', () => {
            if (startY > 0 && currentY - startY > 80) {
                this.app.loadAnalyticsData();
            }
            this.hidePullIndicator();
            startY = 0;
            currentY = 0;
        });
    }
    
    showPullIndicator(distance) {
        // Could show a custom pull-to-refresh indicator
        console.log('Pull distance:', distance);
    }
    
    hidePullIndicator() {
        // Hide pull indicator
    }
}

// Initialize mobile enhancements when in mobile context
if (window.innerWidth <= 767) {
    document.addEventListener('DOMContentLoaded', () => {
        if (window.lumiApp) {
            window.mobileEnhancements = new MobileEnhancements(window.lumiApp);
            window.touchGestures = new TouchGestures(window.lumiApp);
        }
    });
}