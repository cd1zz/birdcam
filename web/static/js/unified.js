// web/static/js/unified.js

// Global state
let currentRegion = null;
let isDrawing = false;
let startX, startY;

// PROCESSING_SERVER_URL is now injected by the template
// No hardcoded URL needed!

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    updateDashboard();
    setInterval(updateDashboard, 5000);
    
    // Initialize live feed error handler
    const liveFeed = document.getElementById('live-feed');
    if (liveFeed) {
        liveFeed.onerror = handleImageError;
    }
});

// Main dashboard update function
async function updateDashboard() {
    await Promise.all([
        updateSystemStatus(),
        updateDetections()
    ]);
}

async function updateSystemStatus() {
    try {
        // Get Pi status
        const piData = await apiCall('/api/status');
        updatePiStatus(piData);
        
        // Get server status (via Pi's proxy)
        const serverData = await apiCall('/api/server-status');
        updateServerStatus(serverData);
        
    } catch (error) {
        console.error('Failed to update status:', error);
        updateStatusError();
    }
}

function updatePiStatus(data) {
    if (!data || !data.pi) return;
    
    const pi = data.pi;
    
    // Update capture status
    const captureStatus = document.getElementById('capture-status');
    const captureText = document.getElementById('capture-text');
    const motionIndicator = document.getElementById('motion-indicator');
    const recordingIndicator = document.getElementById('recording-indicator');
    
    if (pi.is_capturing) {
        captureStatus.className = 'status-indicator recording';
        captureText.textContent = 'RECORDING - Motion detected';
        recordingIndicator.className = 'recording-badge active';
    } else {
        captureStatus.className = 'status-indicator online';
        captureText.textContent = 'MONITORING - Waiting for motion';
        recordingIndicator.className = 'recording-badge';
    }

    if (pi.has_motion) {
        motionIndicator.className = 'motion-badge active';
    } else {
        motionIndicator.className = 'motion-badge';
    }
    
    // Update mini stats
    document.getElementById('pi-total-videos').textContent = pi.total_videos || '-';
    document.getElementById('pi-pending').textContent = pi.pending_sync || '-';
    document.getElementById('pi-storage').textContent = pi.total_size_mb ? Math.round(pi.total_size_mb) : '-';
    
    // Update last motion
    document.getElementById('last-motion').textContent = formatTimestamp(pi.last_motion);
}

function updateServerStatus(data) {
    const serverStatus = document.getElementById('server-status');
    const serverText = document.getElementById('server-text');
    
    if (data && data.server_connected && data.server) {
        const server = data.server;
        
        serverStatus.className = 'status-indicator online';
        if (server.is_processing) {
            serverText.textContent = 'PROCESSING videos...';
        } else {
            const gpu = server.gpu_available ? '🚀 GPU' : '💻 CPU';
            serverText.textContent = `Ready (${gpu})`;
        }
        
        // Update server stats
        document.getElementById('server-processed').textContent = server.processed_videos || '-';
        document.getElementById('server-queue').textContent = server.queue_size || '-';
        document.getElementById('total-birds').textContent = server.total_detections || '-';
        document.getElementById('today-birds').textContent = server.today_detections || '-';
        document.getElementById('avg-time').textContent = server.avg_processing_time || '-';
        
    } else {
        serverStatus.className = 'status-indicator offline';
        serverText.textContent = 'Server offline';
        
        // Clear server stats
        ['server-processed', 'server-queue', 'total-birds', 'today-birds', 'avg-time'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.textContent = '-';
        });
    }
}

function updateStatusError() {
    document.getElementById('capture-text').textContent = 'Connection failed';
    document.getElementById('server-text').textContent = 'Connection failed';
}

async function updateDetections() {
    try {
        const data = await apiCall('/api/server-detections');
        updateDetectionGrid(data.detections || []);
    } catch (error) {
        console.error('Failed to update detections:', error);
        updateDetectionGrid([]);
    }
}

function updateDetectionGrid(detections) {
    const grid = document.getElementById('detection-grid');
    const countBadge = document.getElementById('detection-count');
    
    countBadge.textContent = `${detections.length} detection${detections.length !== 1 ? 's' : ''}`;
    
    if (!detections || detections.length === 0) {
        grid.innerHTML = '<div class="loading-message">No recent detections</div>';
        return;
    }
    
    grid.innerHTML = detections.map(detection => {
        const confidence = detection.confidence * 100;
        const confidenceClass = confidence >= 80 ? 'confidence-high' :
                               confidence >= 60 ? 'confidence-medium' : 'confidence-low';
        
        // Direct thumbnail URL to processing server - much faster!
        const thumbnailUrl = `${PROCESSING_SERVER_URL}/thumbnails/${detection.thumbnail}`;
        
        return `
            <div class="detection-card" onclick="viewVideo('${detection.filename}')">
                <button class="delete-btn" onclick="deleteDetection(event, ${detection.id})">🗑️</button>
                <img src="${thumbnailUrl}"
                     alt="${detection.species || 'Detection'}"
                     onerror="this.style.display='none'">
                <div class="detection-info">
                    <div class="detection-meta">
                        <span><strong>Type:</strong></span>
                        <span class="detection-type">${(detection.species || 'Detection').toUpperCase()}</span>
                    </div>
                    <div class="detection-meta">
                        <span><strong>Confidence:</strong></span>
                        <span class="${confidenceClass}">${confidence.toFixed(1)}%</span>
                    </div>
                    <div class="detection-meta">
                        <span><strong>Time:</strong></span>
                        <span>${detection.timestamp.toFixed(1)}s</span>
                    </div>
                    <div class="detection-meta">
                        <span><strong>Found:</strong></span>
                        <span>${formatTimestamp(detection.received_time)}</span>
                    </div>
                    <div class="filename">${detection.filename}</div>
                </div>
            </div>
        `;
    }).join('');
}

// Control functions
async function syncNow() {
    try {
        const data = await apiCall('/api/sync-now', { method: 'POST' });
        showNotification(data.message || 'Sync started', 'success');
        updateDashboard();
    } catch (error) {
        showNotification('Sync failed', 'error');
    }
}

async function processNow() {
    try {
        const data = await apiCall('/api/process-server-queue', { method: 'POST' });
        showNotification(data.message || 'Processing started', 'success');
        updateDashboard();
    } catch (error) {
        showNotification('Failed to start processing', 'error');
    }
}

function refreshDetections() {
    updateDetections();
}

async function deleteDetection(event, id) {
    event.stopPropagation();
    if (!confirm('Delete this detection?')) return;
    try {
        const data = await apiCall('/api/delete-detection', {
            method: 'POST',
            body: JSON.stringify({ detection_id: id })
        });
        if (data.message) {
            showNotification(data.message, 'success');
            updateDetections();
        } else {
            showNotification(data.error || 'Delete failed', 'error');
        }
    } catch (error) {
        showNotification('Delete failed', 'error');
    }
}

function handleImageError(img) {
    img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAwIiBoZWlnaHQ9IjM3NSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIyMCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkNhbWVyYSBOb3QgQXZhaWxhYmxlPC90ZXh0Pjwvc3ZnPg==';
}

// Settings Modal Functions
function showSettings() {
    const modal = document.getElementById('settings-modal');
    modal.style.display = 'flex';
    
    initializeRegionDrawing();
    loadCurrentSettings();
    
    modal.onclick = (e) => {
        if (e.target === modal) closeSettings();
    };
}

function closeSettings() {
    document.getElementById('settings-modal').style.display = 'none';
}

function initializeRegionDrawing() {
    const canvas = document.getElementById('region-canvas');
    if (!canvas) return;
    
    canvas.onmousedown = null;
    canvas.onmousemove = null;
    canvas.onmouseup = null;
    
    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    
    canvas.addEventListener('touchstart', handleTouch);
    canvas.addEventListener('touchmove', handleTouch);
    canvas.addEventListener('touchend', handleTouch);
}

function startDrawing(e) {
    isDrawing = true;
    const rect = e.target.getBoundingClientRect();
    startX = e.clientX - rect.left;
    startY = e.clientY - rect.top;
}

function draw(e) {
    if (!isDrawing) return;
    
    const canvas = document.getElementById('region-canvas');
    const ctx = canvas.getContext('2d');
    const rect = e.target.getBoundingClientRect();
    
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    ctx.strokeStyle = '#00ff00';
    ctx.lineWidth = 2;
    ctx.strokeRect(startX, startY, currentX - startX, currentY - startY);
    
    ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
    ctx.fillRect(startX, startY, currentX - startX, currentY - startY);
    
    updateRegionInfo();
}

function stopDrawing(e) {
    if (!isDrawing) return;
    isDrawing = false;
    
    const rect = e.target.getBoundingClientRect();
    const endX = e.clientX - rect.left;
    const endY = e.clientY - rect.top;
    
    const scaleX = 640 / 400;
    const scaleY = 480 / 300;
    
    currentRegion = {
        x1: Math.round(Math.min(startX, endX) * scaleX),
        y1: Math.round(Math.min(startY, endY) * scaleY),
        x2: Math.round(Math.max(startX, endX) * scaleX),
        y2: Math.round(Math.max(startY, endY) * scaleY)
    };
    
    updateRegionInfo();
}

function handleTouch(e) {
    e.preventDefault();
    const touch = e.touches[0] || e.changedTouches[0];
    const mouseEvent = new MouseEvent(
        e.type === 'touchstart' ? 'mousedown' : 
        e.type === 'touchmove' ? 'mousemove' : 'mouseup', 
        {
            clientX: touch.clientX,
            clientY: touch.clientY
        }
    );
    e.target.dispatchEvent(mouseEvent);
}

function updateRegionInfo() {
    const info = document.getElementById('region-info');
    if (currentRegion) {
        info.innerHTML = `
            Region: (${currentRegion.x1}, ${currentRegion.y1}) to (${currentRegion.x2}, ${currentRegion.y2})<br>
            Size: ${currentRegion.x2 - currentRegion.x1} x ${currentRegion.y2 - currentRegion.y1} pixels
        `;
    } else {
        info.textContent = 'Draw a region on the image above';
    }
}

function clearRegion() {
    const canvas = document.getElementById('region-canvas');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    currentRegion = null;
    updateRegionInfo();
}

function setDefaultRegion() {
    currentRegion = {
        x1: 128, y1: 96, x2: 512, y2: 384
    };
    
    const canvas = document.getElementById('region-canvas');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const x1 = currentRegion.x1 * 400 / 640;
    const y1 = currentRegion.y1 * 300 / 480;
    const x2 = currentRegion.x2 * 400 / 640;
    const y2 = currentRegion.y2 * 300 / 480;
    
    ctx.strokeStyle = '#00ff00';
    ctx.lineWidth = 2;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
    ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
    ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
    
    updateRegionInfo();
}

async function loadCurrentSettings() {
    try {
        const data = await apiCall('/api/motion-settings');
        
        if (data.region) {
            currentRegion = data.region;
            
            const canvas = document.getElementById('region-canvas');
            const ctx = canvas.getContext('2d');
            
            const x1 = data.region.x1 * 400 / 640;
            const y1 = data.region.y1 * 300 / 480;
            const x2 = data.region.x2 * 400 / 640;
            const y2 = data.region.y2 * 300 / 480;
            
            ctx.strokeStyle = '#00ff00';
            ctx.lineWidth = 2;
            ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
            ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
            ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
            
            updateRegionInfo();
        }
        
        // Load all settings with new timeout parameter
        const thresholdSlider = document.getElementById('threshold-slider');
        const sizeSlider = document.getElementById('size-slider');
        const timeoutSlider = document.getElementById('timeout-slider');
        const thresholdValue = document.getElementById('threshold-value');
        const sizeValue = document.getElementById('size-value');
        const timeoutValue = document.getElementById('timeout-value');
        
        if (thresholdSlider) {
            thresholdSlider.value = data.motion_threshold || 5000;
            thresholdValue.textContent = data.motion_threshold || 5000;
            thresholdSlider.oninput = function() {
                thresholdValue.textContent = this.value;
            };
        }
        
        if (sizeSlider) {
            sizeSlider.value = data.min_contour_area || 500;
            sizeValue.textContent = data.min_contour_area || 500;
            sizeSlider.oninput = function() {
                sizeValue.textContent = this.value;
            };
        }
        
        if (timeoutSlider) {
            timeoutSlider.value = data.motion_timeout_seconds || 30;
            timeoutValue.textContent = data.motion_timeout_seconds || 30;
            timeoutSlider.oninput = function() {
                timeoutValue.textContent = this.value;
            };
        }
        
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function saveSettings() {
    if (!currentRegion) {
        showNotification('Please draw a motion detection region first', 'warning');
        return;
    }
    
    const settings = {
        region: currentRegion,
        motion_threshold: parseInt(document.getElementById('threshold-slider').value),
        min_contour_area: parseInt(document.getElementById('size-slider').value),
        motion_timeout_seconds: parseInt(document.getElementById('timeout-slider').value)
    };
    
    try {
        const data = await apiCall('/api/motion-settings', {
            method: 'POST',
            body: JSON.stringify(settings)
        });
        
        showNotification(data.message || 'Settings saved!', 'success');
        closeSettings();
        updateDashboard();
    } catch (error) {
        showNotification('Failed to save settings', 'error');
    }
}

function testMotion() {
    showNotification('Wave your hand in the detection region and watch the live feed!', 'info');
}

// **UPDATED: Video streaming using template-injected URL**
function viewVideo(filename) {
    // Use the processing server URL injected by the template
    const videoUrl = `${PROCESSING_SERVER_URL}/videos/${filename}`;
    console.log(`🎬 Loading video from configured server: ${videoUrl}`);
    showVideoModal(videoUrl, filename);
}

function showVideoModal(videoUrl, filename) {
    const modal = document.getElementById('video-modal');
    const videoPlayer = document.getElementById('video-player');
    const videoTitle = document.getElementById('video-title');
    const downloadLink = document.getElementById('download-link');
    const newTabLink = document.getElementById('new-tab-link');
    const videoDetails = document.getElementById('video-details');
    
    videoPlayer.src = videoUrl;
    videoTitle.textContent = `📹 ${filename}`;
    
    if (downloadLink) {
        downloadLink.href = videoUrl;
        downloadLink.download = filename;
    }
    
    if (newTabLink) {
        newTabLink.href = videoUrl;
    }
    
    videoPlayer.addEventListener('loadedmetadata', () => {
        if (videoDetails) {
            videoDetails.innerHTML = `
                <strong>Duration:</strong> ${formatDuration(videoPlayer.duration)}<br>
                <strong>Resolution:</strong> ${videoPlayer.videoWidth}x${videoPlayer.videoHeight}<br>
                <strong>File:</strong> ${filename}<br>
                <strong>Source:</strong> ${PROCESSING_SERVER_URL}
            `;
        }
        console.log(`✅ Video loaded successfully from: ${PROCESSING_SERVER_URL}`);
    });
    
    videoPlayer.addEventListener('error', (e) => {
        console.error('Video error:', e);
        if (videoDetails) {
            videoDetails.innerHTML = '<span style="color: red;">❌ Error loading video from processing server</span>';
        }
    });
    
    modal.style.display = 'flex';
    
    modal.onclick = (e) => {
        if (e.target === modal) closeVideoModal();
    };
}

function closeVideoModal() {
    const modal = document.getElementById('video-modal');
    const videoPlayer = document.getElementById('video-player');
    
    modal.style.display = 'none';
    videoPlayer.pause();
    videoPlayer.src = '';
}

async function updateDebugInfo() {
    try {
        const data = await apiCall('/api/motion-debug');
        const debugContent = document.getElementById('debug-content');
        
        if (data.error) {
            debugContent.innerHTML = `<span style="color: #e74c3c;">Error: ${data.error}</span>`;
        } else {
            debugContent.innerHTML = `
                <div><strong>Motion Pixels:</strong> ${data.motion_pixels}</div>
                <div><strong>Contours Found:</strong> ${data.contour_count}</div>
                <div><strong>Largest Contour:</strong> ${data.largest_contour} px²</div>
                <div><strong>Sensitivity Threshold:</strong> ${data.sensitivity_threshold}</div>
                <div><strong>Min Required Size:</strong> ${data.min_contour_area} px²</div>
                <div><strong>Motion Detected:</strong> <span style="color: ${data.motion_detected ? '#27ae60' : '#e74c3c'}">${data.motion_detected ? 'YES' : 'NO'}</span></div>
            `;
        }
        
        debugContent.style.display = 'block';
        
        // Auto-refresh debug info every 2 seconds
        setTimeout(updateDebugInfo, 2000);
        
    } catch (error) {
        console.error('Failed to get debug info:', error);
        const debugContent = document.getElementById('debug-content');
        debugContent.innerHTML = `<span style="color: #e74c3c;">Debug info unavailable</span>`;
        debugContent.style.display = 'block';
    }
}

function toggleDebugInfo() {
    const debugContent = document.getElementById('debug-content');
    if (debugContent.style.display === 'none' || !debugContent.style.display) {
        updateDebugInfo();
    } else {
        debugContent.style.display = 'none';
    }
}