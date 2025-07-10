import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

const Analytics: React.FC = () => {
  const { data: piStatus, error: piError } = useQuery({
    queryKey: ['piStatus'],
    queryFn: async () => {
      const response = await api.status.getPiStatus();
      console.log('Pi Status Response:', response.data);
      return response.data;
    },
    refetchInterval: 5000,
    retry: 1,
  });

  const { data: processingStatus, error: processingError } = useQuery({
    queryKey: ['processingStatus'],
    queryFn: async () => {
      const response = await api.status.getProcessingStatus();
      console.log('Processing Status Response:', response.data);
      return response.data;
    },
    refetchInterval: 5000,
    retry: 1,
  });

  // Log errors for debugging
  if (piError) console.error('Pi Status Error:', piError);
  if (processingError) console.error('Processing Status Error:', processingError);

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
                <span className={`font-medium ${piStatus.status === 'running' ? 'text-green-600' : 'text-red-600'}`}>
                  {piStatus.status === 'running' ? '● Online' : '● Offline'}
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
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
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
                <span className={`font-medium ${processingStatus.status === 'running' ? 'text-green-600' : 'text-red-600'}`}>
                  {processingStatus.status === 'running' ? '● Online' : '● Offline'}
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
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
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