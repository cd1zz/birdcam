// web/static/js/capture.js
/**
 * JavaScript for Capture System Dashboard
 */

// Global state
let currentRegion = null;
let isDrawing = false;
let startX, startY;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    updateStatus();
    setInterval(updateStatus, 5000);
    
    // Error handler for live feed
    const liveFeed = document.getElementById('live-feed');
    if (liveFeed) {
        liveFeed.onerror = handleImageError;
    }
});

// Status update function
async function updateStatus() {
    try {
        const data = await apiCall('/api/status');
        updateStatusDisplay(data);
    } catch (error) {
        console.error('Failed to update status:', error);
        updateStatusDisplay(null);
    }
}

function updateStatusDisplay(data) {
    const captureStatus = document.getElementById('capture-status');
    const captureText = document.getElementById('capture-text');
    const serverStatus = document.getElementById('server-status');
    const serverText = document.getElementById('server-text');
    const queueSize = document.getElementById('queue-size');
    const lastMotion = document.getElementById('last-motion');
    
    if (!data) {
        captureText.textContent = 'Connection failed';
        serverText.textContent = 'Cannot connect';
        return;
    }
    
    // Update capture status
    if (data.pi && data.pi.is_capturing) {
        captureStatus.className = 'status-indicator recording';
        captureText.textContent = 'RECORDING - Motion detected';
    } else {
        captureStatus.className = 'status-indicator online';
        captureText.textContent = 'MONITORING - Waiting for motion';
    }
    
    // Update server status
    if (data.server_connected) {
        serverStatus.className = 'status-indicator online';
        serverText.textContent = 'Processing server connected';
    } else {
        serverStatus.className = 'status-indicator offline';
        serverText.textContent = 'Processing server offline';
    }
    
    // Update other fields
    if (queueSize) queueSize.textContent = data.pi?.queue_size || '-';
    if (lastMotion) lastMotion.textContent = formatTimestamp(data.pi?.last_motion);
}

// Control functions
async function syncNow() {
    try {
        const data = await apiCall('/api/sync-now', { method: 'POST' });
        showNotification(data.message || 'Sync started', 'success');
        updateStatus(); // Refresh status
    } catch (error) {
        showNotification('Sync failed', 'error');
    }
}

function handleImageError(img) {
    img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAwIiBoZWlnaHQ9IjM3NSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIyMCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkNhbWVyYSBOb3QgQXZhaWxhYmxlPC90ZXh0Pjwvc3ZnPg==';
}

// Settings modal functions
function showSettings() {
    const modal = document.getElementById('settings-modal');
    modal.style.display = 'flex';
    
    // Initialize canvas drawing
    initializeRegionDrawing();
    loadCurrentSettings();
    
    // Close on background click
    modal.onclick = (e) => {
        if (e.target === modal) closeSettings();
    };
}

function closeSettings() {
    const modal = document.getElementById('settings-modal');
    modal.style.display = 'none';
}

function initializeRegionDrawing() {
    const canvas = document.getElementById('region-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Remove existing listeners
    canvas.onmousedown = null;
    canvas.onmousemove = null;
    canvas.onmouseup = null;
    
    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    
    // Touch events for mobile
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
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw rectangle
    ctx.strokeStyle = '#00ff00';
    ctx.lineWidth = 2;
    ctx.strokeRect(startX, startY, currentX - startX, currentY - startY);
    
    // Semi-transparent fill
    ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
    ctx.fillRect(startX, startY, currentX - startX, currentY - startY);
    
    updateRegionInfo(startX, startY, currentX, currentY);
}

function stopDrawing(e) {
    if (!isDrawing) return;
    isDrawing = false;
    
    const rect = e.target.getBoundingClientRect();
    const endX = e.clientX - rect.left;
    const endY = e.clientY - rect.top;
    
    // Convert canvas coordinates to camera coordinates (640x480)
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
    // Set to center 60% of frame
    currentRegion = {
        x1: 128,  // 20% of 640
        y1: 96,   // 20% of 480  
        x2: 512,  // 80% of 640
        y2: 384   // 80% of 480
    };
    
    // Draw on canvas
    const canvas = document.getElementById('region-canvas');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Convert to canvas coordinates
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
            // Draw current region on canvas
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
        
        const thresholdSlider = document.getElementById('threshold-slider');
        const sizeSlider = document.getElementById('size-slider');
        const thresholdValue = document.getElementById('threshold-value');
        const sizeValue = document.getElementById('size-value');
        
        if (thresholdSlider) {
            thresholdSlider.value = data.motion_threshold || 5000;
            thresholdValue.textContent = data.motion_threshold || 5000;
        }
        
        if (sizeSlider) {
            sizeSlider.value = data.min_contour_area || 500;
            sizeValue.textContent = data.min_contour_area || 500;
        }
        
        // Update slider values in real-time
        if (thresholdSlider) {
            thresholdSlider.oninput = function() {
                thresholdValue.textContent = this.value;
            };
        }
        
        if (sizeSlider) {
            sizeSlider.oninput = function() {
                sizeValue.textContent = this.value;
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
        min_contour_area: parseInt(document.getElementById('size-slider').value)
    };
    
    try {
        const data = await apiCall('/api/motion-settings', {
            method: 'POST',
            body: JSON.stringify(settings)
        });
        
        showNotification(data.message || 'Settings saved!', 'success');
        closeSettings();
        updateStatus();
    } catch (error) {
        showNotification('Failed to save settings', 'error');
    }
}

function testMotion() {
    showNotification('Wave your hand in the detection region and watch the live feed for motion indicators!', 'info');
}