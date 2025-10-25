// Enhanced Lumi Web Application
class LumiEnhancedApp {
    constructor() {
        this.socket = io();
        this.currentTheme = 'deep-purple';
        this.currentMode = 'light';
        this.currentTab = 'main';
        this.isMobile = this.detectMobile();
        this.services = {};
        this.isOverlayExpanded = false;
        this.vtsStatus = {
            connected: false,
            streaming: false,
            modelLoaded: false
        };
        
        // Camera status
        this.cameraStatus = {
            available: false,
            index: null,
            streaming: false
        };

        // Use MJPG stream instead of WebSocket frames
        this.useMjpgStream = true;
        this.mjpgUrl = '/video_feed'; // Use raw BGR feed (no conversion)
        this.currentStream = null;
        this.streamInitialized = false;
        this.canvasContext = null;
        this.lastFrameTime = 0;
        this.frameInterval = 100; // 10 FPS max
        this.currentImage = null;
        this.isLoading = false;
        
        this.initializeApp();
        this.setupSocketHandlers();
        this.loadInitialData();
    }

    initializeApp() {
        this.setupEventListeners();
        this.initializeTabs();
        this.applyStoredTheme();
        this.initializeServiceMonitoring();
        this.setupImmersiveLayout();
        
        if (this.isMobile) {
            this.initializeMobileFeatures();
        }
        
        console.log('Lumi Enhanced App initialized', { 
            mobile: this.isMobile,
            theme: this.currentTheme,
            mode: this.currentMode,
            mjpgStream: this.useMjpgStream
        });

        // Debug initial state
        setTimeout(() => {
            this.debugLive2D();
        }, 2000);
    }

    debugLive2D() {
        console.log('🔍=== LIVE2D DEBUG INFO ===');
        
        // Check DOM elements
        const live2dDisplay = document.querySelector('.live2d-display');
        const live2dBackground = document.querySelector('.live2d-background');
        
        console.log('📺 .live2d-display element:', live2dDisplay);
        console.log('🎨 .live2d-background element:', live2dBackground);
        
        if (live2dDisplay) {
            console.log('📄 .live2d-display content:', live2dDisplay.innerHTML);
            console.log('👀 .live2d-display visible:', live2dDisplay.offsetParent !== null);
            console.log('📏 .live2d-display dimensions:', {
                width: live2dDisplay.offsetWidth,
                height: live2dDisplay.offsetHeight
            });
        }
        
        console.log('🎬 Streaming method:', this.useMjpgStream ? 'MJPG' : 'WebSocket');
        console.log('📹 MJPG URL:', this.mjpgUrl);
        console.log('🔌 VTS status:', this.vtsStatus);
        console.log('📷 Camera status:', this.cameraStatus);
        console.log('🎨 Canvas context:', this.canvasContext ? 'Available' : 'Not available');
        console.log('🔍=== END DEBUG ===');
    }

    detectMobile() {
        return window.innerWidth <= 767;
    }

    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const tabName = e.currentTarget.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Message input
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');

        sendButton.addEventListener('click', () => this.sendMessage());
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Input auto-resize
        messageInput.addEventListener('input', this.autoResizeTextarea);

        // Theme selection
        document.querySelectorAll('.theme-card').forEach(card => {
            card.addEventListener('click', (e) => {
                const theme = e.currentTarget.dataset.theme;
                this.changeTheme(theme);
            });
        });

        // Service controls
        this.setupServiceControls();
        this.setupCameraControls();

        // Debug button
        this.setupDebugControls();
    }

    setupDebugControls() {
        // Add debug button to the service card
        const vtsCard = document.querySelector('[data-service="vts"]');
        if (vtsCard) {
            const debugButton = document.createElement('button');
            debugButton.className = 'debug-live2d';
            debugButton.style.cssText = 'padding: 6px 12px; font-size: 0.8rem; background: #f59e0b; color: white; border: none; border-radius: 4px; cursor: pointer; margin-top: 8px;';
            debugButton.innerHTML = '<i class="fas fa-bug"></i> Debug Live2D';
            debugButton.addEventListener('click', () => {
                this.debugLive2D();
            });
            vtsCard.appendChild(debugButton);

            // Add stream method toggle
            const streamToggle = document.createElement('button');
            streamToggle.className = 'toggle-stream';
            streamToggle.style.cssText = 'padding: 6px 12px; font-size: 0.8rem; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; margin-top: 8px; margin-left: 8px;';
            streamToggle.innerHTML = '<i class="fas fa-sync"></i> Switch to WebSocket';
            streamToggle.addEventListener('click', () => {
                this.toggleStreamMethod();
            });
            vtsCard.appendChild(streamToggle);
        }
    }

    toggleStreamMethod() {
        this.useMjpgStream = !this.useMjpgStream;
        
        if (this.useMjpgStream) {
            this.mjpgUrl = '/video_feed'; // Raw BGR feed
            this.showNotification('Switched to MJPG Stream (Raw BGR)', 'info');
        } else {
            this.showNotification('Switched to WebSocket Stream', 'info');
        }
        
        // Clean up current stream
        this.cleanupStream();
        
        // Restart the stream
        setTimeout(() => {
            this.initializeLive2DStream();
        }, 100);
    }

    cleanupStream() {
        // Clear any intervals
        if (this.mjpgRefreshInterval) {
            clearInterval(this.mjpgRefreshInterval);
            this.mjpgRefreshInterval = null;
        }
        
        // Clear any timeouts
        if (this.canvasRenderTimeout) {
            clearTimeout(this.canvasRenderTimeout);
            this.canvasRenderTimeout = null;
        }
        
        // Disconnect WebSocket if connected
        if (this.live2dSocket && this.live2dSocket.connected) {
            this.live2dSocket.disconnect();
            this.live2dSocket = null;
        }
        
        // Clear current stream
        this.currentStream = null;
        this.streamInitialized = false;
        this.currentImage = null;
        this.isLoading = false;
    }

    setupImmersiveLayout() {
        this.setupOverlayInteractions();
        this.initializeLive2DBackground();
    }

    setupOverlayInteractions() {
        const expandToggle = document.getElementById('expand-toggle');
        const chatOverlay = document.querySelector('.chat-overlay');
        const overlayHeader = document.querySelector('.overlay-header');
        
        if (expandToggle && chatOverlay) {
            expandToggle.addEventListener('click', () => {
                this.toggleOverlay();
            });
        }
        
        // Header click to toggle on mobile
        if (overlayHeader && this.isMobile) {
            overlayHeader.addEventListener('click', () => {
                this.toggleOverlay();
            });
        }
        
        // Swipe to expand on mobile
        if (this.isMobile) {
            this.setupSwipeToExpand();
        }
    }

    toggleOverlay() {
        const chatOverlay = document.querySelector('.chat-overlay');
        const expandToggle = document.getElementById('expand-toggle');
        
        if (chatOverlay && expandToggle) {
            this.isOverlayExpanded = !this.isOverlayExpanded;
            chatOverlay.classList.toggle('expanded', this.isOverlayExpanded);
            
            const icon = expandToggle.querySelector('i');
            if (this.isOverlayExpanded) {
                icon.className = 'fas fa-chevron-down';
                // Focus input when expanded
                setTimeout(() => {
                    const messageInput = document.getElementById('message-input');
                    if (messageInput) messageInput.focus();
                }, 300);
            } else {
                icon.className = 'fas fa-chevron-up';
            }
        }
    }

    setupSwipeToExpand() {
        const overlayHeader = document.querySelector('.overlay-header');
        const chatOverlay = document.querySelector('.chat-overlay');
        
        if (!overlayHeader || !chatOverlay) return;
        
        let startY = 0;
        let currentY = 0;
        let isSwiping = false;
        
        overlayHeader.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
            isSwiping = true;
        }, { passive: true });
        
        overlayHeader.addEventListener('touchmove', (e) => {
            if (!isSwiping) return;
            
            currentY = e.touches[0].clientY;
            const diff = startY - currentY;
            
            // Visual feedback during swipe
            if (Math.abs(diff) > 10) {
                e.preventDefault();
                this.updateSwipeVisualFeedback(diff);
            }
        });
        
        overlayHeader.addEventListener('touchend', () => {
            if (!isSwiping) return;
            
            const diff = startY - currentY;
            const minSwipeDistance = 40;
            
            if (Math.abs(diff) > minSwipeDistance) {
                if (diff > 0 && !this.isOverlayExpanded) {
                    // Swipe up - expand
                    this.toggleOverlay();
                } else if (diff < 0 && this.isOverlayExpanded) {
                    // Swipe down - collapse
                    this.toggleOverlay();
                }
            }
            
            this.clearSwipeVisualFeedback();
            isSwiping = false;
            startY = 0;
            currentY = 0;
        });
    }

    updateSwipeVisualFeedback(diff) {
        const chatOverlay = document.querySelector('.chat-overlay');
        if (!chatOverlay) return;
        
        // Add subtle visual feedback during swipe
        if (diff > 0 && !this.isOverlayExpanded) {
            chatOverlay.style.transform = `translateY(-${Math.min(diff * 0.5, 20)}px)`;
        } else if (diff < 0 && this.isOverlayExpanded) {
            chatOverlay.style.transform = `translateY(${Math.min(Math.abs(diff) * 0.5, 20)}px)`;
        }
    }

    clearSwipeVisualFeedback() {
        const chatOverlay = document.querySelector('.chat-overlay');
        if (chatOverlay) {
            chatOverlay.style.transform = '';
        }
    }

    initializeLive2DBackground() {
        // Initialize Live2D background streaming
        const live2dBackground = document.querySelector('.live2d-background');
        if (live2dBackground) {
            // Add dynamic background based on theme
            this.updateBackgroundGradient();
        }
        
        // Connect to Live2D streaming
        this.initializeLive2DStream();
    }

    initializeLive2DStream() {
        const live2dDisplay = document.querySelector('.live2d-display');
        if (!live2dDisplay) {
            console.error('❌ Live2D display element not found');
            return;
        }

        // Prevent multiple initializations
        if (this.streamInitialized) {
            console.log('🔄 Stream already initialized, skipping...');
            return;
        }

        this.streamInitialized = true;

        // Create canvas for smooth rendering
        this.setupCanvas();

        if (this.useMjpgStream) {
            this.initializeMjpgStream();
        } else {
            this.initializeWebSocketStream();
        }
    }

    setupCanvas() {
        const live2dDisplay = document.querySelector('.live2d-display');
        
        // Clear existing content
        live2dDisplay.innerHTML = '';
        
        // Create canvas element
        const canvas = document.createElement('canvas');
        canvas.className = 'stream-canvas';
        canvas.style.cssText = `
            width: 100%; 
            height: 100%; 
            display: block;
            background: transparent;
        `;
        
        // Set canvas size to match display
        const updateCanvasSize = () => {
            const rect = live2dDisplay.getBoundingClientRect();
            canvas.width = rect.width;
            canvas.height = rect.height;
        };

        // Initial size and resize handler
        updateCanvasSize();
        window.addEventListener('resize', updateCanvasSize);
        
        // Get context
        this.canvasContext = canvas.getContext('2d', { alpha: false });
        this.canvasContext.imageSmoothingEnabled = true;
        this.canvasContext.imageSmoothingQuality = 'high';
        
        live2dDisplay.appendChild(canvas);
        this.currentStream = canvas;
        
        console.log('🎨 Canvas setup complete:', { width: canvas.width, height: canvas.height });
    }

    drawToCanvas(image) {
        if (!this.canvasContext || !this.currentStream) return;
        
        const canvas = this.currentStream;
        const ctx = this.canvasContext;
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Calculate aspect ratio and positioning
        const imgAspect = image.width / image.height;
        const canvasAspect = canvas.width / canvas.height;
        
        let renderWidth, renderHeight, offsetX, offsetY;
        
        if (imgAspect > canvasAspect) {
            // Image is wider than canvas
            renderWidth = canvas.width;
            renderHeight = canvas.width / imgAspect;
            offsetX = 0;
            offsetY = (canvas.height - renderHeight) / 2;
        } else {
            // Image is taller than canvas
            renderHeight = canvas.height;
            renderWidth = canvas.height * imgAspect;
            offsetX = (canvas.width - renderWidth) / 2;
            offsetY = 0;
        }
        
        // Draw image centered and scaled properly
        ctx.drawImage(image, offsetX, offsetY, renderWidth, renderHeight);
    }

    initializeMjpgStream() {
        console.log('🎬 Starting MJPG stream:', this.mjpgUrl);
        
        // Create hidden image element for loading
        const loaderImg = new Image();
        loaderImg.crossOrigin = 'anonymous';
        
        let isFirstLoad = true;
        
        const loadNextFrame = () => {
            if (!this.useMjpgStream || this.isLoading) return;
            
            this.isLoading = true;
            const timestamp = new Date().getTime();
            loaderImg.src = this.mjpgUrl + '?t=' + timestamp;
        };
        
        loaderImg.onload = () => {
            this.isLoading = false;
            
            // Throttle frame rate
            const now = Date.now();
            if (now - this.lastFrameTime < this.frameInterval) {
                // Skip this frame, try again soon
                setTimeout(loadNextFrame, this.frameInterval - (now - this.lastFrameTime));
                return;
            }
            
            this.lastFrameTime = now;
            
            // Draw to canvas
            this.drawToCanvas(loaderImg);
            
            if (isFirstLoad) {
                console.log('✅ MJPG stream loaded successfully');
                this.updateLive2DStatus('mjpg_stream');
                isFirstLoad = false;
            }
            
            // Load next frame
            setTimeout(loadNextFrame, this.frameInterval);
        };
        
        loaderImg.onerror = (e) => {
            this.isLoading = false;
            console.error('❌ MJPG stream error:', e);
            this.updateLive2DStatus('error');
            
            // Retry after delay
            setTimeout(() => {
                if (this.useMjpgStream) {
                    loadNextFrame();
                }
            }, 1000);
        };
        
        // Start loading frames
        loadNextFrame();
        this.updateLive2DStatus('mjpg_stream');
    }

    initializeWebSocketStream() {
        console.log('🎬 Starting WebSocket stream');
        
        // Clear any existing MJPG refresh interval
        if (this.mjpgRefreshInterval) {
            clearInterval(this.mjpgRefreshInterval);
            this.mjpgRefreshInterval = null;
        }

        // Connect to Live2D namespace
        this.live2dSocket = io('/live2d');
        
        let frameCount = 0;
        let pendingFrame = null;
        
        this.live2dSocket.on('connect', () => {
            console.log('✅ Connected to Live2D WebSocket namespace');
            // Request camera status immediately
            this.live2dSocket.emit('get_camera_status');
            // Start the stream
            setTimeout(() => {
                this.live2dSocket.emit('start_background_stream');
            }, 500);
        });
        
        this.live2dSocket.on('connected', (data) => {
            console.log('✅ Live2D WebSocket stream connected', data);
            this.updateCameraStatus({
                available: data.camera_available || false,
                index: data.camera_index || null
            });
            
            if (data.vts_connected) {
                this.updateVTSStatus({
                    connected: true,
                    streaming: data.vts_connected,
                    modelLoaded: true
                });
            }
        });

        this.live2dSocket.on('live2d_frame', (data) => {
            frameCount++;
            
            // Throttle frame rate
            const now = Date.now();
            if (now - this.lastFrameTime < this.frameInterval) {
                pendingFrame = data.frame;
                return;
            }
            
            this.lastFrameTime = now;
            this.processWebSocketFrame(data.frame);
            
            // Process any pending frame
            if (pendingFrame) {
                setTimeout(() => {
                    this.processWebSocketFrame(pendingFrame);
                    pendingFrame = null;
                }, this.frameInterval);
            }
        });
        
        this.live2dSocket.on('emotion_updated', (data) => {
            this.updateBackgroundEmotion(data.emotion);
        });
        
        this.live2dSocket.on('camera_status', (data) => {
            console.log('📷 Camera status update:', data);
            this.updateCameraStatus(data);
        });
        
        this.live2dSocket.on('camera_scan_results', (data) => {
            console.log('🔍 Camera scan results:', data);
            this.showNotification(`Found ${data.total_cameras} camera(s)`, 'info');
            this.updateCameraStatus({
                available: data.camera_initialized,
                index: data.current_camera_index
            });
        });
        
        this.live2dSocket.on('streaming_status', (data) => {
            console.log('🎬 Streaming status:', data);
            this.updateCameraStatus({
                streaming: data.streaming,
                available: data.camera_available
            });
        });

        this.live2dSocket.on('vts_connected', (data) => {
            console.log('✅ VTS connection status:', data);
            this.updateVTSStatus({
                connected: data.connected,
                streaming: data.connected,
                modelLoaded: data.connected
            });
        });

        this.live2dSocket.on('connected_clients', (count) => {
            console.log(`👥 Live2D clients connected: ${count}`);
        });

        this.live2dSocket.on('vts_error', (data) => {
            console.error('❌ VTS error:', data.error);
            this.showNotification(`VTS Error: ${data.error}`, 'error');
        });

        // Start background stream after a short delay
        setTimeout(() => {
            if (this.live2dSocket && this.live2dSocket.connected) {
                this.live2dSocket.emit('start_background_stream');
                console.log('🚀 Requested Live2D WebSocket stream start');
            }
        }, 1000);

        this.updateLive2DStatus('virtual_camera');
    }

    processWebSocketFrame(frameData) {
        if (!frameData || !frameData.startsWith('data:image/')) {
            return;
        }

        // Create image and draw to canvas
        const img = new Image();
        img.onload = () => {
            this.drawToCanvas(img);
            this.updateLive2DStatus('virtual_camera');
        };
        
        img.onerror = (e) => {
            console.error('❌ Failed to load WebSocket frame:', e);
            this.updateLive2DStatus('error');
        };
        
        img.src = frameData;
    }

    updateLive2DStatus(source) {
        const statusElement = document.getElementById('live2d-status');
        if (!statusElement) return;
        
        let statusText = '';
        let statusClass = '';
        
        switch(source) {
            case 'mjpg_stream':
                statusText = '🖥️ MJPG Stream';
                statusClass = 'status-online';
                break;
            case 'virtual_camera':
                statusText = '📡 WebSocket Stream';
                statusClass = 'status-online';
                break;
            case 'placeholder':
                statusText = '📷 Camera Setup Required';
                statusClass = 'status-offline';
                break;
            case 'error':
                statusText = '❌ Stream Error';
                statusClass = 'status-error';
                break;
            default:
                statusText = '🔌 Connecting...';
                statusClass = 'status-offline';
        }
        
        statusElement.textContent = statusText;
        statusElement.className = `live2d-status ${statusClass}`;
    }

    updateCameraStatus(status) {
        this.cameraStatus = { ...this.cameraStatus, ...status };
        
        // Update service card
        this.updateServiceCard('vts', {
            online: this.cameraStatus.available || this.vtsStatus.connected,
            details: this.cameraStatus.available ? 
                `Camera ${this.cameraStatus.index} active` : 
                this.vtsStatus.connected ? 'VTS connected' : 'Camera not found'
        });
        
        // Update Live2D status display
        const statusSource = this.useMjpgStream ? 'mjpg_stream' : 'virtual_camera';
        this.updateLive2DStatus(this.cameraStatus.available ? statusSource : 'placeholder');
        
        // Show notification if camera becomes available
        if (status.available && !this.cameraStatus._wasAvailable) {
            this.showNotification('✅ Virtual camera connected!', 'success');
        }
        this.cameraStatus._wasAvailable = status.available;
    }

    updateBackgroundEmotion(emotion) {
        const background = document.querySelector('.live2d-background');
        if (background) {
            // Remove previous emotion classes
            background.className = background.className.replace(/\bemotion-\S+/g, '');
            // Add current emotion class
            background.classList.add(`emotion-${emotion}`);
        }
    }

    updateVTSStatus(status) {
        this.vtsStatus = { ...this.vtsStatus, ...status };
        
        let statusText = 'VTS Disconnected';
        let details = 'Not connected to VTube Studio';
        
        if (status.connected) {
            statusText = 'VTS Connected';
            details = 'Live2D model streaming';
            if (status.modelLoaded) {
                details = 'Model loaded & streaming';
            }
        } else if (status.source === 'virtual_camera' || status.source === 'mjpg_stream') {
            statusText = 'Virtual Camera';
            details = 'Using virtual camera feed';
        } else if (status.source === 'placeholder') {
            statusText = 'Setup Required';
            details = 'Virtual camera setup needed';
        }
        
        this.updateServiceCard('vts', {
            online: status.connected || status.source === 'virtual_camera' || status.source === 'mjpg_stream',
            details: details
        });

        // Update main socket with VTS status
        this.socket.emit('vts_status_update', this.vtsStatus);
    }

    updateBackgroundGradient() {
        const background = document.querySelector('.live2d-background');
        if (background) {
            // Update gradient based on current theme
            const style = document.createElement('style');
            style.id = 'dynamic-background';
            style.textContent = `
                .live2d-background {
                    background: linear-gradient(135deg, 
                        var(--primary-color) 0%, 
                        var(--primary-dark) 50%, 
                        var(--primary-light) 100%
                    );
                    transition: background 1s ease-in-out;
                }
                .live2d-background.emotion-happy {
                    background: linear-gradient(135deg, #10b981 0%, #059669 50%, #34d399 100%);
                }
                .live2d-background.emotion-curious {
                    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 50%, #60a5fa 100%);
                }
                .live2d-background.emotion-excited {
                    background: linear-gradient(135deg, #f59e0b 0%, #d97706 50%, #fbbf24 100%);
                }
                .live2d-background.emotion-thoughtful {
                    background: linear-gradient(135deg, #6366f1 0%, #4338ca 50%, #818cf8 100%);
                }
                .live2d-background.emotion-neutral {
                    background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 50%, var(--primary-light) 100%);
                }
                .live2d-status {
                    position: absolute;
                    bottom: 10px;
                    left: 10px;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.8rem;
                    z-index: 10;
                    background: rgba(0, 0, 0, 0.7);
                    color: white;
                }
                .live2d-status.status-online {
                    background: rgba(16, 185, 129, 0.9);
                }
                .live2d-status.status-offline {
                    background: rgba(107, 114, 128, 0.9);
                }
                .live2d-status.status-error {
                    background: rgba(239, 68, 68, 0.9);
                }
                .stream-canvas {
                    transition: opacity 0.3s ease-in-out;
                }
            `;
            
            // Remove existing dynamic background style
            const existingStyle = document.getElementById('dynamic-background');
            if (existingStyle) {
                existingStyle.remove();
            }
            
            document.head.appendChild(style);
            
            // Add status indicator if it doesn't exist
            if (!document.getElementById('live2d-status')) {
                const statusElement = document.createElement('div');
                statusElement.id = 'live2d-status';
                statusElement.className = 'live2d-status status-offline';
                statusElement.textContent = '🔌 Connecting...';
                background.appendChild(statusElement);
            }
        }
    }

    setupServiceControls() {
        // Service toggle buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('service-toggle')) {
                const service = e.target.dataset.service;
                this.toggleService(service, e.target.checked);
            }
            
            if (e.target.classList.contains('test-connection')) {
                const service = e.target.dataset.service;
                this.testServiceConnection(service);
            }

            if (e.target.classList.contains('connect-vts')) {
                this.connectToVTS();
            }
        });
    }

    setupCameraControls() {
        // Add camera scan button to the service card
        const vtsCard = document.querySelector('[data-service="vts"]');
        if (vtsCard) {
            const cameraControls = document.createElement('div');
            cameraControls.className = 'camera-controls';
            cameraControls.style.cssText = 'margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap;';
            cameraControls.innerHTML = `
                <button class="scan-cameras" style="padding: 6px 12px; font-size: 0.8rem; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer;">
                    <i class="fas fa-search"></i> Scan Cameras
                </button>
                <button class="start-stream" style="padding: 6px 12px; font-size: 0.8rem; background: var(--success-color); color: white; border: none; border-radius: 4px; cursor: pointer;">
                    <i class="fas fa-play"></i> Start Stream
                </button>
                <button class="setup-guide" style="padding: 6px 12px; font-size: 0.8rem; background: var(--accent-color); color: white; border: none; border-radius: 4px; cursor: pointer;">
                    <i class="fas fa-question-circle"></i> Setup Guide
                </button>
            `;
            vtsCard.appendChild(cameraControls);

            // Add event listeners
            vtsCard.querySelector('.scan-cameras').addEventListener('click', () => {
                this.scanCameras();
            });
            
            vtsCard.querySelector('.start-stream').addEventListener('click', () => {
                this.startLive2DStream();
            });
            
            vtsCard.querySelector('.setup-guide').addEventListener('click', () => {
                this.showCameraSetupGuide();
            });
        }
    }

    scanCameras() {
        if (this.live2dSocket) {
            this.live2dSocket.emit('scan_cameras');
            this.showNotification('Scanning for cameras...', 'info');
        }
    }

    startLive2DStream() {
        this.cleanupStream();
        this.streamInitialized = false;
        
        setTimeout(() => {
            this.initializeLive2DStream();
            this.showNotification('Restarting stream...', 'info');
        }, 100);
    }

    showCameraSetupGuide() {
        const guide = `
Virtual Camera Setup Guide:

Option 1: VTube Studio Virtual Camera
1. Open VTube Studio → Settings → Virtual Camera
2. Enable "Virtual Camera" and click "Start"
3. Restart Lumi AI

Option 2: OBS Virtual Camera (More Stable)
1. Install OBS Studio (free)
2. Add VTube Studio as a Window Capture source
3. Go to Tools → VirtualCam → Start
4. Restart Lumi AI

After setup, click "Scan Cameras" to detect your virtual camera.
`;
        
        alert(guide);
    }

    async connectToVTS() {
        try {
            this.socket.emit('connect_to_vts');
            if (this.live2dSocket) {
                this.live2dSocket.emit('connect_to_vts');
            }
            this.showNotification('Connecting to VTube Studio...', 'info');
        } catch (error) {
            console.error('Error connecting to VTS:', error);
            this.showNotification('Failed to connect to VTube Studio', 'error');
        }
    }

    initializeTabs() {
        // Show initial tab
        this.switchTab('main');
        
        // Update tab indicators
        this.updateTabIndicators();
    }

    switchTab(tabName) {
        // Hide all tab contents
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // Remove active class from all tab buttons
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active');
        });
        
        // Show selected tab content
        const targetTab = document.getElementById(`${tabName}-tab`);
        const targetButton = document.querySelector(`[data-tab="${tabName}"]`);
        
        if (targetTab && targetButton) {
            targetTab.classList.add('active');
            targetButton.classList.add('active');
            this.currentTab = tabName;
            
            // Tab-specific initializations
            this.onTabSwitch(tabName);
        }
    }

    onTabSwitch(tabName) {
        switch(tabName) {
            case 'main':
                this.focusMessageInput();
                // Reinitialize stream when switching to main tab
                setTimeout(() => {
                    if (!this.streamInitialized) {
                        this.initializeLive2DStream();
                    }
                }, 500);
                break;
            case 'analytics':
                this.loadAnalyticsData();
                break;
            case 'appearance':
                this.loadThemeGallery();
                break;
        }
    }

    updateTabIndicators() {
        // Could add notification badges, etc.
    }

    autoResizeTextarea(e) {
        const textarea = e.target;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    focusMessageInput() {
        const messageInput = document.getElementById('message-input');
        if (messageInput && this.isOverlayExpanded) {
            messageInput.focus();
        }
    }

    async sendMessage() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        
        if (!message) return;

        // Add user message to chat
        this.addMessage(message, 'user');
        messageInput.value = '';
        this.resetTextarea();
        this.showTypingIndicator();

        // Disable send button during processing
        const sendButton = document.getElementById('send-button');
        sendButton.disabled = true;

        // Auto-expand overlay on mobile when sending message
        if (this.isMobile && !this.isOverlayExpanded) {
            this.toggleOverlay();
        }

        try {
            // Send via Socket.IO
            this.socket.emit('chat_message', { message: message });
        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage('Sorry, I encountered an error. Please try again.', 'ai');
            this.hideTypingIndicator();
            sendButton.disabled = false;
        }
    }

    addMessage(text, sender) {
        const chatMessages = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = `message-bubble ${sender}`;
        bubbleDiv.textContent = text;
        
        messageDiv.appendChild(bubbleDiv);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Add animation
        messageDiv.style.animation = 'slideInUp 0.3s ease';
    }

    showTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.classList.remove('hidden');
        }
    }

    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.classList.add('hidden');
        }
        
        // Re-enable send button
        const sendButton = document.getElementById('send-button');
        sendButton.disabled = false;
    }

    resetTextarea() {
        const messageInput = document.getElementById('message-input');
        messageInput.style.height = 'auto';
    }

    // Theme Management
    applyStoredTheme() {
        const storedTheme = localStorage.getItem('lumi-theme') || 'deep-purple';
        const storedMode = localStorage.getItem('lumi-mode') || 'light';
        
        this.changeTheme(storedTheme, storedMode, false);
    }

    async changeTheme(themeName, mode = null, save = true) {
        // Remove previous theme
        document.documentElement.removeAttribute('data-theme');
        document.documentElement.removeAttribute('data-mode');
        
        // Apply new theme
        document.documentElement.setAttribute('data-theme', themeName);
        if (mode) {
            document.documentElement.setAttribute('data-mode', mode);
            this.currentMode = mode;
        }
        
        this.currentTheme = themeName;
        
        // Update theme cards
        this.updateThemeSelection(themeName);
        
        // Update background gradient
        this.updateBackgroundGradient();
        
        // Save to localStorage
        if (save) {
            localStorage.setItem('lumi-theme', themeName);
            localStorage.setItem('lumi-mode', this.currentMode);
        }
        
        // Notify server if needed
        this.socket.emit('theme_changed', { 
            theme: themeName, 
            mode: this.currentMode 
        });
    }

    updateThemeSelection(activeTheme) {
        document.querySelectorAll('.theme-card').forEach(card => {
            card.classList.toggle('active', card.dataset.theme === activeTheme);
        });
    }

    loadThemeGallery() {
        // Theme gallery is static for now, could be dynamic
    }

    // Service Management
    initializeServiceMonitoring() {
        // Start monitoring services
        this.monitorServices();
        
        // Set up periodic updates
        setInterval(() => this.monitorServices(), 30000); // Every 30 seconds
    }

    async monitorServices() {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();
            
            this.updateServiceStatus(status);
            
            // Also check VTS status specifically
            await this.checkVTSStatus();
        } catch (error) {
            console.error('Error monitoring services:', error);
            this.updateServiceStatus({ status: 'error' });
        }
    }

    async checkVTSStatus() {
        try {
            const response = await fetch('/api/vts_status');
            const status = await response.json();
            
            this.updateVTSStatus({
                connected: status.vts_connected || false,
                streaming: status.streaming || false,
                modelLoaded: status.vts_connected || false
            });
            
            this.updateCameraStatus({
                available: status.camera_available || false,
                index: status.camera_index || null
            });
            
            // If VTS is connected but not streaming, start streaming
            if (status.vts_connected && !status.streaming && this.live2dSocket) {
                this.live2dSocket.emit('start_background_stream');
            }
        } catch (error) {
            console.error('Error checking VTS status:', error);
        }
    }

    updateServiceStatus(statusData) {
        // Update Ollama status
        this.updateServiceCard('ollama', {
            online: statusData.features?.ai_engine || false,
            details: `Model: ${statusData.config?.ollama_model || 'Unknown'}`,
            responseTime: '--'
        });
        
        // Update Discord status
        this.updateServiceCard('discord', {
            online: statusData.config?.discord_enabled || false,
            details: statusData.config?.discord_enabled ? 'Bot connected' : 'Bot disabled'
        });
        
        // Update VTS status - Use actual VTS connection status
        this.updateServiceCard('vts', {
            online: this.vtsStatus.connected || this.cameraStatus.available,
            details: this.vtsStatus.connected ? 'VTS connected & streaming' : 
                    this.cameraStatus.available ? 'Virtual camera active' : 'VTS disconnected'
        });
        
        // Update Plugins status
        this.updateServiceCard('plugins', {
            online: statusData.plugins ? true : false,
            details: `Enabled: ${statusData.plugins?.enabled || 0}/${statusData.plugins?.loaded || 0}`
        });
    }

    updateServiceCard(service, data) {
        const card = document.querySelector(`[data-service="${service}"]`);
        if (!card) return;
        
        const statusElement = card.querySelector('.service-status');
        const detailsElement = card.querySelector('.service-details');
        const indicator = card.querySelector('.status-indicator');
        
        if (statusElement && detailsElement && indicator) {
            // Update status indicator
            indicator.className = 'status-indicator';
            indicator.classList.add(data.online ? 'status-online' : 'status-offline');
            
            // Update status text
            const statusText = statusElement.querySelector('span:last-child');
            if (statusText) {
                statusText.textContent = data.online ? 'Online' : 'Offline';
            }
            
            // Update details
            detailsElement.textContent = data.details;
        }
    }

    async toggleService(service, enabled) {
        // Implement service toggling logic
        console.log(`Toggling ${service} to ${enabled}`);
        // This would make API calls to enable/disable services
    }

    async testServiceConnection(service) {
        // Implement connection testing
        console.log(`Testing connection for ${service}`);
    }

    // Analytics
    async loadAnalyticsData() {
        try {
            const response = await fetch('/api/dashboard');
            const data = await response.json();
            
            this.updateAnalyticsDisplay(data);
        } catch (error) {
            console.error('Error loading analytics:', error);
        }
    }

    updateAnalyticsDisplay(data) {
        // Update metrics grid
        this.updateMetric('total-messages', data.metrics?.conversation_metrics?.total_messages || 0);
        this.updateMetric('interaction-quality', data.metrics?.interaction_quality || 0);
        this.updateMetric('avg-words', Math.round(data.metrics?.user_engagement?.avg_words_per_message || 0));
        this.updateMetric('relationship-level', Math.round((data.metrics?.relationship_progress?.familiarity_level || 0) * 100));
    }

    updateMetric(metricId, value) {
        const element = document.getElementById(metricId);
        if (element) {
            element.textContent = value;
        }
    }

    // Mobile Features
    initializeMobileFeatures() {
        this.setupTouchGestures();
        this.optimizeForMobile();
    }

    setupTouchGestures() {
        // Swipe between tabs
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
            const minSwipeDistance = 60;
            
            if (Math.abs(diff) > minSwipeDistance) {
                if (diff > 0) {
                    this.swipeLeft();
                } else {
                    this.swipeRight();
                }
            }
        });
    }

    swipeLeft() {
        const tabs = ['main', 'analytics', 'appearance'];
        const currentIndex = tabs.indexOf(this.currentTab);
        if (currentIndex < tabs.length - 1) {
            this.switchTab(tabs[currentIndex + 1]);
        }
    }

    swipeRight() {
        const tabs = ['main', 'analytics', 'appearance'];
        const currentIndex = tabs.indexOf(this.currentTab);
        if (currentIndex > 0) {
            this.switchTab(tabs[currentIndex - 1]);
        }
    }

    optimizeForMobile() {
        // Add mobile-specific optimizations
        document.body.classList.add('mobile');
        
        // Auto-expand overlay on mobile when switching to main tab
        if (this.currentTab === 'main') {
            setTimeout(() => {
                this.toggleOverlay();
            }, 500);
        }
    }

    // Socket.IO Handlers
    setupSocketHandlers() {
        this.socket.on('connect', () => {
            this.updateConnectionStatus(true);
            console.log('✅ Connected to server');
        });
        
        this.socket.on('disconnect', () => {
            this.updateConnectionStatus(false);
            console.log('❌ Disconnected from server');
        });
        
        this.socket.on('chat_response', (data) => {
            this.hideTypingIndicator();
            this.addMessage(data.response, 'ai');
        });
        
        this.socket.on('chat_error', (data) => {
            this.hideTypingIndicator();
            this.addMessage('Sorry, I encountered an error. Please try again.', 'ai');
        });
        
        this.socket.on('dashboard_update', (data) => {
            this.updateAnalyticsDisplay(data);
        });
        
        this.socket.on('service_status', (data) => {
            this.updateServiceStatus(data);
        });

        // VTS-specific events
        this.socket.on('vts_connection_update', (data) => {
            this.updateVTSStatus(data);
        });

        this.socket.on('vts_status_update', (data) => {
            this.updateVTSStatus(data);
        });

        this.socket.on('vts_connected', (data) => {
            this.showNotification('VTube Studio connected successfully!', 'success');
            this.updateVTSStatus({
                connected: true,
                streaming: true,
                modelLoaded: true
            });
        });

        this.socket.on('vts_error', (data) => {
            this.showNotification(`VTS Error: ${data.error}`, 'error');
        });
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('connection-status');
        if (indicator) {
            indicator.textContent = connected ? '● Online' : '● Offline';
            indicator.style.color = connected ? 'var(--success-color)' : 'var(--error-color)';
        }
    }

    showNotification(message, type = 'info') {
        // Simple notification system
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'};
            color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-lg);
            z-index: 10000;
            animation: slideInRight 0.3s ease;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    loadInitialData() {
        // Load initial service status
        this.monitorServices();
        
        // Load initial analytics
        this.loadAnalyticsData();
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.lumiApp = new LumiEnhancedApp();
});

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LumiEnhancedApp;
}