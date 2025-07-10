import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

interface SystemHealth {
  isOnline: boolean;
  lastSeen: number;
  consecutiveFailures: number;
}

const Analytics: React.FC = () => {
  const [piHealth, setPiHealth] = useState<SystemHealth>({ isOnline: false, lastSeen: 0, consecutiveFailures: 0 });
  const [processingHealth, setProcessingHealth] = useState<SystemHealth>({ isOnline: false, lastSeen: 0, consecutiveFailures: 0 });

  const { data: piStatus, error: piError, isError: piIsError } = useQuery({
    queryKey: ['piStatus'],
    queryFn: api.status.getPiStatus,
    refetchInterval: 15000, // Reduced frequency from 5s to 15s
    retry: 3, // Increased retries from 1 to 3
    retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 10000), // Exponential backoff
    staleTime: 10000, // Data considered fresh for 10s
    cacheTime: 30000, // Keep in cache for 30s
    refetchOnWindowFocus: false, // Don't refetch on window focus
    onSuccess: (data) => {
      setPiHealth(prev => ({
        isOnline: true,
        lastSeen: Date.now(),
        consecutiveFailures: 0
      }));
    },
    onError: (error) => {
      setPiHealth(prev => ({
        ...prev,
        consecutiveFailures: prev.consecutiveFailures + 1,
        isOnline: prev.consecutiveFailures < 3 // Only mark offline after 3 consecutive failures
      }));
    }
  });

  const { data: processingStatus, error: processingError, isError: processingIsError } = useQuery({
    queryKey: ['processingStatus'],
    queryFn: api.status.getProcessingStatus,
    refetchInterval: 15000, // Reduced frequency from 5s to 15s
    retry: 3, // Increased retries from 1 to 3
    retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 10000), // Exponential backoff
    staleTime: 10000, // Data considered fresh for 10s
    cacheTime: 30000, // Keep in cache for 30s
    refetchOnWindowFocus: false, // Don't refetch on window focus
    onSuccess: (data) => {
      setProcessingHealth(prev => ({
        isOnline: true,
        lastSeen: Date.now(),
        consecutiveFailures: 0
      }));
    },
    onError: (error) => {
      setProcessingHealth(prev => ({
        ...prev,
        consecutiveFailures: prev.consecutiveFailures + 1,
        isOnline: prev.consecutiveFailures < 3 // Only mark offline after 3 consecutive failures
      }));
    }
  });

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
                <span className="font-medium">{formatUptime(piStatus.uptime)}</span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Active Cameras</span>
                <span className="font-medium">{piStatus.cameras_active}</span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Videos Today</span>
                <span className="font-medium">{piStatus.videos_today}</span>
              </div>
              
              <div className="pt-4 border-t">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-600">Storage</span>
                  <span className="text-sm text-gray-500">
                    {formatBytes(piStatus.storage_used)} / {formatBytes(piStatus.storage_total)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{ width: `${(piStatus.storage_used / piStatus.storage_total) * 100}%` }}
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
                <span className="font-medium">{formatUptime(processingStatus.uptime)}</span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Detections Today</span>
                <span className="font-medium">{processingStatus.detections_today}</span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Videos Processed</span>
                <span className="font-medium">{processingStatus.videos_today}</span>
              </div>
              
              <div className="pt-4 border-t">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-600">Storage</span>
                  <span className="text-sm text-gray-500">
                    {formatBytes(processingStatus.storage_used)} / {formatBytes(processingStatus.storage_total)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-green-600 h-2 rounded-full transition-all"
                    style={{ width: `${(processingStatus.storage_used / processingStatus.storage_total) * 100}%` }}
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

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="text-blue-600 text-3xl mb-2">📹</div>
          <p className="text-sm text-gray-600">Total Videos</p>
          <p className="text-2xl font-semibold text-gray-900">
            {(piStatus?.videos_today || 0) + (processingStatus?.videos_today || 0)}
          </p>
        </div>
        
        <div className="bg-green-50 rounded-lg p-4">
          <div className="text-green-600 text-3xl mb-2">🦅</div>
          <p className="text-sm text-gray-600">Wildlife Detected</p>
          <p className="text-2xl font-semibold text-gray-900">
            {processingStatus?.detections_today || 0}
          </p>
        </div>
        
        <div className="bg-purple-50 rounded-lg p-4">
          <div className="text-purple-600 text-3xl mb-2">📷</div>
          <p className="text-sm text-gray-600">Active Cameras</p>
          <p className="text-2xl font-semibold text-gray-900">
            {piStatus?.cameras_active || 0}
          </p>
        </div>
        
        <div className="bg-orange-50 rounded-lg p-4">
          <div className="text-orange-600 text-3xl mb-2">⏱️</div>
          <p className="text-sm text-gray-600">System Uptime</p>
          <p className="text-2xl font-semibold text-gray-900">
            {piStatus ? formatUptime(piStatus.uptime) : '—'}
          </p>
        </div>
      </div>
    </div>
  );
};

export default Analytics;