// web/static/js/processing.js
/**
 * JavaScript for Processing System Dashboard
 */

// Detect mobile browsers for download compatibility
function isMobileBrowser() {
    return /Mobi|Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

// Fetch file and trigger download (used on mobile)
async function triggerDownload(url, filename) {
    const response = await fetch(url);
    const blob = await response.blob();
    const tempUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = tempUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(tempUrl);
}
// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    updateDashboard();
    setInterval(updateDashboard, 10000);
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
        const data = await apiCall('/api/status');
        updateStatusDisplay(data);
    } catch (error) {
        console.error('Failed to update status:', error);
        updateStatusDisplay(null);
    }
}

function updateStatusDisplay(data) {
    if (!data) {
        // Handle error state
        document.getElementById('total-videos').textContent = '-';
        document.getElementById('processed-videos').textContent = '-';
        document.getElementById('queue-size').textContent = '-';
        return;
    }
    
    // Update statistics
    document.getElementById('total-videos').textContent = data.total_videos || '-';
    document.getElementById('processed-videos').textContent = data.processed_videos || '-';
    document.getElementById('queue-size').textContent = data.queue_size || '-';
    
    const totalBirds = document.getElementById('total-birds');
    const todayBirds = document.getElementById('today-birds');
    const avgTime = document.getElementById('avg-time');
    
    if (totalBirds) totalBirds.textContent = data.total_birds || '-';
    if (todayBirds) todayBirds.textContent = data.today_birds || '-';
    if (avgTime) avgTime.textContent = data.avg_processing_time || '-';
    
    // Update system status
    const statusDiv = document.getElementById('system-status');
    if (statusDiv) {
        if (data.is_processing) {
            statusDiv.innerHTML = '<span class="status-indicator processing"></span>PROCESSING videos...';
        } else {
            const gpu = data.gpu_available ? '🚀 GPU' : '💻 CPU';
            statusDiv.innerHTML = `<span class="status-indicator online"></span>Ready (${gpu})`;
        }
    }
}

async function updateDetections() {
    try {
        const data = await apiCall('/api/recent-detections');
        updateDetectionGrid(data.detections || []);
    } catch (error) {
        console.error('Failed to update detections:', error);
        updateDetectionGrid([]);
    }
}

function updateDetectionGrid(detections) {
    const grid = document.getElementById('detection-grid');
    
    if (!detections || detections.length === 0) {
        grid.innerHTML = '<div class="loading-message">No recent detections</div>';
        return;
    }
    
    grid.innerHTML = detections.map(detection => {
        const countBadge = detection.count && detection.count > 1
            ? `<span class="count-badge">${detection.count}</span>` : '';
        return `
        <div class="detection-card" onclick="viewVideo('${detection.filename}')">
            ${countBadge}
            <img src="/thumbnails/${detection.thumbnail}"
                 alt="Bird detection"
                 onerror="this.style.display='none'">
            <div class="detection-info">
                <div><strong>Confidence:</strong> <span>${(detection.confidence * 100).toFixed(1)}%</span></div>
                <div><strong>Time:</strong> <span>${detection.timestamp.toFixed(1)}s</span></div>
                <div><strong>Found:</strong> <span>${formatTimestamp(detection.received_time)}</span></div>
                <div class="filename"><strong>File:</strong> ${detection.filename}</div>
            </div>
        </div>`;
    }).join('');
}

// Control functions
async function processNow() {
    try {
        const data = await apiCall('/api/process-now', { method: 'POST' });
        showNotification(data.message || 'Processing started', 'success');
        updateDashboard(); // Refresh dashboard
    } catch (error) {
        showNotification('Failed to start processing', 'error');
    }
}

// Video viewing functions
function viewVideo(filename) {
    const videoUrl = `/videos/${filename}`;
    showVideoModal(videoUrl, filename);
}

function showVideoModal(videoUrl, filename) {
    const modal = document.getElementById('video-modal');
    const videoPlayer = document.getElementById('video-player');
    const videoTitle = document.getElementById('video-title');
    const downloadLink = document.getElementById('download-link');
    const newTabLink = document.getElementById('new-tab-link');
    const videoDetails = document.getElementById('video-details');
    
    // Set video source
    videoPlayer.src = videoUrl;
    videoTitle.textContent = `📹 ${filename}`;
    
    // Set download links
    if (downloadLink) {
        downloadLink.href = videoUrl;
        downloadLink.download = filename;
        downloadLink.onclick = null;
        if (isMobileBrowser()) {
            downloadLink.addEventListener('click', async (e) => {
                e.preventDefault();
                try {
                    await triggerDownload(videoUrl, filename);
                } catch (err) {
                    console.error('Download failed:', err);
                    window.open(videoUrl, '_blank');
                }
            }, { once: true });
        }
    }
    
    if (newTabLink) {
        newTabLink.href = videoUrl;
    }
    
    // Add video event listeners
    videoPlayer.addEventListener('loadedmetadata', () => {
        if (videoDetails) {
            videoDetails.innerHTML = `
                <strong>Duration:</strong> ${formatDuration(videoPlayer.duration)}<br>
                <strong>Resolution:</strong> ${videoPlayer.videoWidth}x${videoPlayer.videoHeight}<br>
                <strong>File:</strong> ${filename}
            `;
        }
    });
    
    videoPlayer.addEventListener('error', (e) => {
        console.error('Video error:', e);
        if (videoDetails) {
            videoDetails.innerHTML = '<span style="color: red;">❌ Error loading video</span>';
        }
    });
    
    // Show modal
    modal.style.display = 'flex';
    
    // Close on background click
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