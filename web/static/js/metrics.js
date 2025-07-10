/**
 * System Metrics Display Component
 * Displays CPU, memory, and disk usage with visual indicators
 */

class SystemMetrics {
    constructor(containerId, apiEndpoint = '/api/system-metrics') {
        this.container = document.getElementById(containerId);
        this.apiEndpoint = apiEndpoint;
        this.updateInterval = 5000; // 5 seconds
        this.intervalId = null;
        this.init();
    }

    init() {
        this.createMetricsHTML();
        this.startUpdating();
    }

    createMetricsHTML() {
        this.container.innerHTML = `
            <div class="metrics-container">
                <div class="metrics-header">
                    <h3>📊 System Metrics</h3>
                    <div class="metrics-refresh">
                        <button class="btn btn-sm btn-secondary" onclick="window.systemMetrics.updateMetrics()">
                            🔄 Refresh
                        </button>
                    </div>
                </div>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-icon">💻</div>
                        <div class="metric-info">
                            <div class="metric-label">CPU</div>
                            <div class="metric-value" id="cpu-value">--</div>
                            <div class="metric-bar">
                                <div class="metric-fill" id="cpu-fill"></div>
                            </div>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">🧠</div>
                        <div class="metric-info">
                            <div class="metric-label">Memory</div>
                            <div class="metric-value" id="memory-value">--</div>
                            <div class="metric-bar">
                                <div class="metric-fill" id="memory-fill"></div>
                            </div>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">💾</div>
                        <div class="metric-info">
                            <div class="metric-label">Disk</div>
                            <div class="metric-value" id="disk-value">--</div>
                            <div class="metric-bar">
                                <div class="metric-fill" id="disk-fill"></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="metrics-footer">
                    <small id="metrics-timestamp">Last updated: --</small>
                </div>
            </div>
        `;
    }

    startUpdating() {
        this.updateMetrics();
        this.intervalId = setInterval(() => this.updateMetrics(), this.updateInterval);
    }

    stopUpdating() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    async updateMetrics() {
        try {
            const response = await fetch(this.apiEndpoint);
            const data = await response.json();
            
            if (data.error) {
                console.error('Metrics error:', data.error);
                this.showError(data.error);
                return;
            }

            this.updateDisplay(data);
        } catch (error) {
            console.error('Failed to fetch metrics:', error);
            this.showError('Failed to fetch metrics');
        }
    }

    updateDisplay(metrics) {
        // CPU
        const cpuValue = document.getElementById('cpu-value');
        const cpuFill = document.getElementById('cpu-fill');
        if (cpuValue && cpuFill) {
            cpuValue.textContent = `${metrics.cpu_percent}%`;
            cpuFill.style.width = `${metrics.cpu_percent}%`;
            cpuFill.className = `metric-fill ${this.getColorClass(metrics.cpu_percent)}`;
        }

        // Memory
        const memoryValue = document.getElementById('memory-value');
        const memoryFill = document.getElementById('memory-fill');
        if (memoryValue && memoryFill) {
            memoryValue.textContent = `${metrics.memory_percent}%`;
            memoryValue.title = `${metrics.memory_used_gb}GB / ${metrics.memory_total_gb}GB`;
            memoryFill.style.width = `${metrics.memory_percent}%`;
            memoryFill.className = `metric-fill ${this.getColorClass(metrics.memory_percent)}`;
        }

        // Disk
        const diskValue = document.getElementById('disk-value');
        const diskFill = document.getElementById('disk-fill');
        if (diskValue && diskFill) {
            diskValue.textContent = `${metrics.disk_percent}%`;
            diskValue.title = `${metrics.disk_used_gb}GB / ${metrics.disk_total_gb}GB (${metrics.disk_free_gb}GB free)`;
            diskFill.style.width = `${metrics.disk_percent}%`;
            diskFill.className = `metric-fill ${this.getColorClass(metrics.disk_percent)}`;
        }

        // Timestamp
        const timestampElement = document.getElementById('metrics-timestamp');
        if (timestampElement) {
            const date = new Date(metrics.timestamp * 1000);
            timestampElement.textContent = `Last updated: ${date.toLocaleTimeString()}`;
        }
    }

    getColorClass(percentage) {
        if (percentage >= 90) return 'danger';
        if (percentage >= 75) return 'warning';
        return 'success';
    }

    showError(message) {
        const cpuValue = document.getElementById('cpu-value');
        const memoryValue = document.getElementById('memory-value');
        const diskValue = document.getElementById('disk-value');
        
        if (cpuValue) cpuValue.textContent = 'Error';
        if (memoryValue) memoryValue.textContent = 'Error';
        if (diskValue) diskValue.textContent = 'Error';
        
        const timestampElement = document.getElementById('metrics-timestamp');
        if (timestampElement) {
            timestampElement.textContent = `Error: ${message}`;
        }
    }

    destroy() {
        this.stopUpdating();
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Auto-initialize if metrics container exists
    const metricsContainer = document.getElementById('system-metrics');
    if (metricsContainer) {
        window.systemMetrics = new SystemMetrics('system-metrics');
    }
});