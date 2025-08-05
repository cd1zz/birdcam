import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type SystemStatus } from '../api/client';

interface SystemHealth {
  isOnline: boolean;
  lastSeen: number;
  consecutiveFailures: number;
}

const Analytics: React.FC = () => {
  const queryClient = useQueryClient();
  const [piHealth, setPiHealth] = useState<SystemHealth>({ isOnline: false, lastSeen: 0, consecutiveFailures: 0 });
  const [processingHealth, setProcessingHealth] = useState<SystemHealth>({ isOnline: false, lastSeen: 0, consecutiveFailures: 0 });

  const { data: piStatus } = useQuery<SystemStatus>({
    queryKey: ['piStatus'],
    queryFn: api.status.getPiStatus,
    refetchInterval: 15000, // Reduced frequency from 5s to 15s
    retry: 3, // Increased retries from 1 to 3
    retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 10000), // Exponential backoff
    staleTime: 10000, // Data considered fresh for 10s
    gcTime: 30000, // Keep in cache for 30s (replaces cacheTime)
    refetchOnWindowFocus: false, // Don't refetch on window focus
  });

  const { data: processingStatus } = useQuery<SystemStatus>({
    queryKey: ['processingStatus'],
    queryFn: api.status.getProcessingStatus,
    refetchInterval: 15000, // Reduced frequency from 5s to 15s
    retry: 3, // Increased retries from 1 to 3
    retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 10000), // Exponential backoff
    staleTime: 10000, // Data considered fresh for 10s
    gcTime: 30000, // Keep in cache for 30s (replaces cacheTime)
    refetchOnWindowFocus: false, // Don't refetch on window focus
  });


  // Handle success/error states with useEffect
  useEffect(() => {
    if (piStatus) {
      setPiHealth({
        isOnline: true,
        lastSeen: Date.now(),
        consecutiveFailures: 0
      });
    }
  }, [piStatus]);

  useEffect(() => {
    if (processingStatus) {
      setProcessingHealth({
        isOnline: true,
        lastSeen: Date.now(),
        consecutiveFailures: 0
      });
    }
  }, [processingStatus]);

  // Initialize health states
  useEffect(() => {
    if (piStatus && piHealth.lastSeen === 0) {
      setPiHealth({ isOnline: true, lastSeen: Date.now(), consecutiveFailures: 0 });
    }
    if (processingStatus && processingHealth.lastSeen === 0) {
      setProcessingHealth({ isOnline: true, lastSeen: Date.now(), consecutiveFailures: 0 });
    }
  }, [piStatus, processingStatus, piHealth.lastSeen, processingHealth.lastSeen]);

  // Determine connection status with more resilience
  const getPiConnectionStatus = () => {
    if (piStatus && piHealth.isOnline) return 'online';
    if (piHealth.consecutiveFailures >= 3) return 'offline';
    return 'checking';
  };

  const getProcessingConnectionStatus = () => {
    if (processingStatus && processingHealth.isOnline) return 'online';
    if (processingHealth.consecutiveFailures >= 3) return 'offline';
    return 'checking';
  };

  // Manual trigger mutations
  const syncMutation = useMutation({
    mutationFn: api.system.triggerSync,
    onSuccess: () => {
      // Refresh status after sync
      queryClient.invalidateQueries({ queryKey: ['piStatus'] });
      queryClient.invalidateQueries({ queryKey: ['processingStatus'] });
    },
  });

  const processingMutation = useMutation({
    mutationFn: api.processing.triggerProcessing,
    onSuccess: () => {
      // Refresh processing status
      queryClient.invalidateQueries({ queryKey: ['processingStatus'] });
    },
  });

  const cleanupMutation = useMutation({
    mutationFn: api.processing.triggerCleanup,
    onSuccess: () => {
      // Refresh processing status  
      queryClient.invalidateQueries({ queryKey: ['processingStatus'] });
    },
  });

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Manual Controls - Moved to top */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
          <span className="text-2xl">🎛️</span>
          Manual Controls
        </h3>
        
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
          {/* Sync Files Button */}
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending || getPiConnectionStatus() !== 'online'}
            className={`flex flex-col sm:flex-row items-center justify-center gap-2 px-3 sm:px-4 py-3 rounded-lg transition-all text-center sm:text-left ${
              syncMutation.isPending 
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                : getPiConnectionStatus() !== 'online'
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                : 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/30 border border-blue-200 dark:border-blue-800'
            }`}
          >
            {syncMutation.isPending ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span>Syncing...</span>
              </>
            ) : (
              <>
                <span className="text-xl">🔄</span>
                <div>
                  <div className="font-medium text-sm sm:text-base">Sync Files</div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 hidden sm:block">Pi → AI Server</div>
                </div>
              </>
            )}
          </button>

          {/* Process Videos Button */}
          <button
            onClick={() => processingMutation.mutate()}
            disabled={processingMutation.isPending || getProcessingConnectionStatus() !== 'online'}
            className={`flex flex-col sm:flex-row items-center justify-center gap-2 px-3 sm:px-4 py-3 rounded-lg transition-all text-center sm:text-left ${
              processingMutation.isPending
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                : getProcessingConnectionStatus() !== 'online'
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                : 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 hover:bg-green-100 dark:hover:bg-green-900/30 border border-green-200 dark:border-green-800'
            }`}
          >
            {processingMutation.isPending ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-600"></div>
                <span>Processing...</span>
              </>
            ) : (
              <>
                <span className="text-xl">🤖</span>
                <div>
                  <div className="font-medium text-sm sm:text-base">Process Videos</div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 hidden sm:block">Run AI Analysis</div>
                </div>
              </>
            )}
          </button>

          {/* Cleanup Button */}
          <button
            onClick={() => cleanupMutation.mutate()}
            disabled={cleanupMutation.isPending || getProcessingConnectionStatus() !== 'online'}
            className={`flex flex-col sm:flex-row items-center justify-center gap-2 px-3 sm:px-4 py-3 rounded-lg transition-all text-center sm:text-left ${
              cleanupMutation.isPending
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                : getProcessingConnectionStatus() !== 'online'
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                : 'bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 hover:bg-orange-100 dark:hover:bg-orange-900/30 border border-orange-200 dark:border-orange-800'
            }`}
          >
            {cleanupMutation.isPending ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-orange-600"></div>
                <span>Cleaning...</span>
              </>
            ) : (
              <>
                <span className="text-xl">🧹</span>
                <div>
                  <div className="font-medium text-sm sm:text-base">Cleanup Files</div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 hidden sm:block">Remove Old Videos</div>
                </div>
              </>
            )}
          </button>
        </div>

        {/* Status Messages */}
        <div className="mt-4 space-y-2">
          {syncMutation.isError && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-2 text-sm text-red-700 dark:text-red-300">
              ❌ Sync failed: {(syncMutation.error as Error)?.message || 'Connection error'}
            </div>
          )}
          {syncMutation.isSuccess && (
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded p-2 text-sm text-green-700 dark:text-green-300">
              File sync triggered successfully
            </div>
          )}
          
          {processingMutation.isError && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-2 text-sm text-red-700 dark:text-red-300">
              ❌ Processing failed: {(processingMutation.error as Error)?.message || 'Connection error'}
            </div>
          )}
          {processingMutation.isSuccess && (
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded p-2 text-sm text-green-700 dark:text-green-300">
              AI processing triggered successfully
            </div>
          )}
          
          {cleanupMutation.isError && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-2 text-sm text-red-700 dark:text-red-300">
              ❌ Cleanup failed: {(cleanupMutation.error as Error)?.message || 'Connection error'}
            </div>
          )}
          {cleanupMutation.isSuccess && (
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded p-2 text-sm text-green-700 dark:text-green-300">
              Cleanup triggered successfully
            </div>
          )}
        </div>
      </div>

      {/* System Status Panes - Moved below Manual Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pi Camera System */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
            <span className="text-2xl">📷</span>
            Pi Camera System
          </h3>
          
          {piStatus ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-300">Status</span>
                <span className={`font-medium ${
                  getPiConnectionStatus() === 'online' ? 'text-green-600' : 
                  getPiConnectionStatus() === 'checking' ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {getPiConnectionStatus() === 'online' ? '● Online' : 
                   getPiConnectionStatus() === 'checking' ? '● Checking...' : '● Offline'}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-300">Uptime</span>
                <span className="font-medium text-gray-900 dark:text-white">{formatUptime(piStatus.uptime || 0)}</span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-300">Active Cameras</span>
                <span className="font-medium text-gray-900 dark:text-white">{piStatus.cameras_active || 0}</span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-300">Videos Today</span>
                <span className="font-medium text-gray-900 dark:text-white">{piStatus.videos_today || 0}</span>
              </div>
              
              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-600 dark:text-gray-300">Storage (System Boot Drive)</span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {formatBytes(piStatus.storage_used || 0)} / {formatBytes(piStatus.storage_total || 0)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{ width: `${((piStatus.storage_used || 0) / (piStatus.storage_total || 1)) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-32">
              {getPiConnectionStatus() === 'offline' ? (
                <div className="text-center">
                  <div className="text-red-500 text-3xl mb-2">⚠️</div>
                  <p className="text-red-600 dark:text-red-400 font-medium">Connection Failed</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    After {piHealth.consecutiveFailures} attempts
                  </p>
                </div>
              ) : (
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              )}
            </div>
          )}
        </div>

        {/* Processing Server */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
            <span className="text-2xl">🤖</span>
            AI Processing Server
          </h3>
          
          {processingStatus ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-300">Status</span>
                <span className={`font-medium ${
                  getProcessingConnectionStatus() === 'online' ? 'text-green-600' : 
                  getProcessingConnectionStatus() === 'checking' ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {getProcessingConnectionStatus() === 'online' ? '● Online' : 
                   getProcessingConnectionStatus() === 'checking' ? '● Checking...' : '● Offline'}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-300">Uptime</span>
                <span className="font-medium text-gray-900 dark:text-white">{formatUptime(processingStatus.uptime || 0)}</span>
              </div>
              
              {/* Enhanced Processing Queue Info */}
              {processingStatus.queue && (
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Processing Queue</span>
                    <span className={`text-xs px-2 py-1 rounded ${
                      processingStatus.queue.is_processing ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                    }`}>
                      {processingStatus.queue.is_processing ? 'Active' : 'Idle'}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-1 sm:gap-2 text-xs sm:text-sm">
                    <div className="text-center">
                      <div className="font-medium text-yellow-600">{processingStatus.queue.pending}</div>
                      <div className="text-gray-500 dark:text-gray-400">Pending</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium text-blue-600">{processingStatus.queue.processing}</div>
                      <div className="text-gray-500 dark:text-gray-400">Processing</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium text-red-600">{processingStatus.queue.failed}</div>
                      <div className="text-gray-500 dark:text-gray-400">Failed</div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Performance Metrics */}
              {processingStatus.performance && (
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 space-y-2">
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300">Performance</div>
                  <div className="grid grid-cols-2 gap-2 sm:gap-3 text-xs sm:text-sm">
                    <div>
                      <div className="font-medium text-blue-600">
                        {processingStatus.performance.processing_rate_hour}/hr
                      </div>
                      <div className="text-gray-500 dark:text-gray-400">Processing Rate</div>
                    </div>
                    <div>
                      <div className="font-medium text-blue-600">
                        {processingStatus.performance.avg_processing_time.toFixed(1)}s
                      </div>
                      <div className="text-gray-500 dark:text-gray-400">Avg Time</div>
                    </div>
                    <div>
                      <div className="font-medium text-green-600">
                        {(processingStatus.performance.detection_rate * 100).toFixed(1)}%
                      </div>
                      <div className="text-gray-500 dark:text-gray-400">Detection Rate</div>
                    </div>
                    <div>
                      <div className="font-medium text-purple-600">
                        {processingStatus.performance.session_processed}
                      </div>
                      <div className="text-gray-500 dark:text-gray-400">Session Total</div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* System Resources */}
              {processingStatus.system && (
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 space-y-2">
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300">System Resources</div>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-600 dark:text-gray-300">CPU</span>
                      <span className="font-medium text-gray-900 dark:text-white">{processingStatus.system.cpu_percent.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div 
                        className="bg-green-600 h-2 rounded-full transition-all"
                        style={{ width: `${processingStatus.system.cpu_percent}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-600 dark:text-gray-300">Memory</span>
                      <span className="font-medium text-gray-900 dark:text-white">{processingStatus.system.memory_percent.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div 
                        className="bg-green-600 h-2 rounded-full transition-all"
                        style={{ width: `${processingStatus.system.memory_percent}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Disk Storage with Roles */}
              {processingStatus.system?.disks && processingStatus.system.disks.length > 0 ? (
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300">Storage Disks</div>
                  {processingStatus.system.disks.map((disk: {
                    device: string;
                    mountpoint: string;
                    role: string;
                    percent: number;
                    used_gb: number;
                    total_gb: number;
                  }, index: number) => (
                    <div key={disk.device || index} className="space-y-1">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600 dark:text-gray-300 flex items-center gap-1">
                          {disk.role === 'storage' && <span title="Storage disk">💾</span>}
                          {disk.role === 'boot' && <span title="Boot disk">🖥️</span>}
                          {disk.role === 'other' && <span title="Other disk">💿</span>}
                          <span className="font-medium">
                            {disk.role === 'storage' ? 'Storage' : 
                             disk.role === 'boot' ? 'System' : 
                             disk.mountpoint}
                          </span>
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {formatBytes(disk.used_gb * 1024 * 1024 * 1024)} / {formatBytes(disk.total_gb * 1024 * 1024 * 1024)}
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                        <div 
                          className={`h-1.5 rounded-full transition-all ${
                            disk.percent > 90 ? 'bg-red-600' :
                            disk.percent > 75 ? 'bg-orange-600' :
                            'bg-green-600'
                          }`}
                          style={{ width: `${disk.percent}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                // Fallback to simple storage display if disk metrics not available
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-600 dark:text-gray-300">Storage</span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {formatBytes(processingStatus.storage_used || 0)} / {formatBytes(processingStatus.storage_total || 0)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div 
                      className="bg-green-600 h-2 rounded-full transition-all"
                      style={{ width: `${((processingStatus.storage_used || 0) / (processingStatus.storage_total || 1)) * 100}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-32">
              {getProcessingConnectionStatus() === 'offline' ? (
                <div className="text-center">
                  <div className="text-red-500 text-3xl mb-2">⚠️</div>
                  <p className="text-red-600 dark:text-red-400 font-medium">Connection Failed</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    After {processingHealth.consecutiveFailures} attempts
                  </p>
                </div>
              ) : (
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
              )}
            </div>
          )}
        </div>
      </div>

    </div>
  );
};

export default Analytics;