import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, type SystemStatus } from '../api/client';

interface SystemHealth {
  isOnline: boolean;
  lastSeen: number;
  consecutiveFailures: number;
}

const Analytics: React.FC = () => {
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
    <div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Pi Camera System */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">📷</span>
            Pi Camera System
          </h3>
          
          {piStatus ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Status</span>
                <span className={`font-medium ${
                  getPiConnectionStatus() === 'online' ? 'text-green-600' : 
                  getPiConnectionStatus() === 'checking' ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {getPiConnectionStatus() === 'online' ? '● Online' : 
                   getPiConnectionStatus() === 'checking' ? '● Checking...' : '● Offline'}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Uptime</span>
                <span className="font-medium">{formatUptime(piStatus.uptime || 0)}</span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Active Cameras</span>
                <span className="font-medium">{piStatus.cameras_active || 0}</span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Videos Today</span>
                <span className="font-medium">{piStatus.videos_today || 0}</span>
              </div>
              
              <div className="pt-4 border-t">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-600">Storage</span>
                  <span className="text-sm text-gray-500">
                    {formatBytes(piStatus.storage_used || 0)} / {formatBytes(piStatus.storage_total || 0)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
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
                  <p className="text-red-600 font-medium">Connection Failed</p>
                  <p className="text-sm text-gray-500 mt-1">
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
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">🤖</span>
            AI Processing Server
          </h3>
          
          {processingStatus ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Status</span>
                <span className={`font-medium ${
                  getProcessingConnectionStatus() === 'online' ? 'text-green-600' : 
                  getProcessingConnectionStatus() === 'checking' ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {getProcessingConnectionStatus() === 'online' ? '● Online' : 
                   getProcessingConnectionStatus() === 'checking' ? '● Checking...' : '● Offline'}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Uptime</span>
                <span className="font-medium">{formatUptime(processingStatus.uptime || 0)}</span>
              </div>
              
              {/* Enhanced Processing Queue Info */}
              {processingStatus.queue && (
                <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-700">Processing Queue</span>
                    <span className={`text-xs px-2 py-1 rounded ${
                      processingStatus.queue.is_processing ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {processingStatus.queue.is_processing ? 'Active' : 'Idle'}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div className="text-center">
                      <div className="font-medium text-yellow-600">{processingStatus.queue.pending}</div>
                      <div className="text-gray-500">Pending</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium text-blue-600">{processingStatus.queue.processing}</div>
                      <div className="text-gray-500">Processing</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium text-red-600">{processingStatus.queue.failed}</div>
                      <div className="text-gray-500">Failed</div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Performance Metrics */}
              {processingStatus.performance && (
                <div className="bg-blue-50 rounded-lg p-3 space-y-2">
                  <div className="text-sm font-medium text-gray-700">Performance</div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <div className="font-medium text-blue-600">
                        {processingStatus.performance.processing_rate_hour}/hr
                      </div>
                      <div className="text-gray-500">Processing Rate</div>
                    </div>
                    <div>
                      <div className="font-medium text-blue-600">
                        {processingStatus.performance.avg_processing_time.toFixed(1)}s
                      </div>
                      <div className="text-gray-500">Avg Time</div>
                    </div>
                    <div>
                      <div className="font-medium text-green-600">
                        {(processingStatus.performance.detection_rate * 100).toFixed(1)}%
                      </div>
                      <div className="text-gray-500">Detection Rate</div>
                    </div>
                    <div>
                      <div className="font-medium text-purple-600">
                        {processingStatus.performance.session_processed}
                      </div>
                      <div className="text-gray-500">Session Total</div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* System Resources */}
              {processingStatus.system && (
                <div className="bg-green-50 rounded-lg p-3 space-y-2">
                  <div className="text-sm font-medium text-gray-700">System Resources</div>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-600">CPU</span>
                      <span className="font-medium">{processingStatus.system.cpu_percent.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-green-600 h-2 rounded-full transition-all"
                        style={{ width: `${processingStatus.system.cpu_percent}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-600">Memory</span>
                      <span className="font-medium">{processingStatus.system.memory_percent.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-green-600 h-2 rounded-full transition-all"
                        style={{ width: `${processingStatus.system.memory_percent}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="pt-4 border-t">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-600">Storage</span>
                  <span className="text-sm text-gray-500">
                    {formatBytes(processingStatus.storage_used || 0)} / {formatBytes(processingStatus.storage_total || 0)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-green-600 h-2 rounded-full transition-all"
                    style={{ width: `${((processingStatus.storage_used || 0) / (processingStatus.storage_total || 1)) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-32">
              {getProcessingConnectionStatus() === 'offline' ? (
                <div className="text-center">
                  <div className="text-red-500 text-3xl mb-2">⚠️</div>
                  <p className="text-red-600 font-medium">Connection Failed</p>
                  <p className="text-sm text-gray-500 mt-1">
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

      {/* Enhanced Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="text-blue-600 text-3xl mb-2">📹</div>
          <p className="text-sm text-gray-600">Videos Today</p>
          <p className="text-2xl font-semibold text-gray-900">
            {(piStatus?.videos_today || 0) + (processingStatus?.videos_today || 0)}
          </p>
        </div>
        
        <div className="bg-green-50 rounded-lg p-4">
          <div className="text-green-600 text-3xl mb-2">🦅</div>
          <p className="text-sm text-gray-600">Detections Today</p>
          <p className="text-2xl font-semibold text-gray-900">
            {processingStatus?.detections_today || 0}
          </p>
        </div>
        
        <div className="bg-purple-50 rounded-lg p-4">
          <div className="text-purple-600 text-3xl mb-2">📊</div>
          <p className="text-sm text-gray-600">Total Processed</p>
          <p className="text-2xl font-semibold text-gray-900">
            {processingStatus?.totals?.videos_processed || 0}
          </p>
        </div>
        
        <div className="bg-yellow-50 rounded-lg p-4">
          <div className="text-yellow-600 text-3xl mb-2">⏳</div>
          <p className="text-sm text-gray-600">Queue Length</p>
          <p className="text-2xl font-semibold text-gray-900">
            {processingStatus?.queue?.pending || 0}
          </p>
        </div>
        
        <div className="bg-orange-50 rounded-lg p-4">
          <div className="text-orange-600 text-3xl mb-2">⚡</div>
          <p className="text-sm text-gray-600">Processing Rate</p>
          <p className="text-2xl font-semibold text-gray-900">
            {processingStatus?.performance?.processing_rate_hour || 0}/hr
          </p>
        </div>
      </div>
    </div>
  );
};

export default Analytics;