import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import CameraFeed from '../components/CameraFeed';
import { api } from '../api/client';

const LiveFeeds: React.FC = () => {
  const [selectedLayout, setSelectedLayout] = useState<'grid' | 'single'>('grid');
  const [selectedCamera, setSelectedCamera] = useState<number | null>(null);

  const { 
    data: cameras, 
    isLoading, 
    error,
    isError 
  } = useQuery({
    queryKey: ['cameras'],
    queryFn: api.cameras.list, // Direct function reference - cleaner
    refetchInterval: 30000,
    retry: 3,
    retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  useEffect(() => {
    if (cameras && cameras.length > 0 && !selectedCamera) {
      setSelectedCamera(cameras[0].id);
    }
  }, [cameras, selectedCamera]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-300">Loading cameras...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    const errorMessage = (error as Error)?.message || 'Failed to load cameras. Please check your connection.';
    
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <span className="text-red-500 text-xl">⚠️</span>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Connection Error</h3>
            <p className="text-red-700 dark:text-red-300 mt-1">{errorMessage}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!cameras || cameras.length === 0) {
    return (
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <span className="text-yellow-500 text-xl">⚠️</span>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">No Cameras Found</h3>
            <p className="text-yellow-700 dark:text-yellow-300 mt-1">
              No cameras are currently configured. Please check your camera setup.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Controls */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Camera Feeds</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">{cameras.length} camera{cameras.length > 1 ? 's' : ''} active</p>
          </div>
          
          <div className="flex items-center gap-2 sm:gap-4">
            {/* Layout Toggle */}
            <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setSelectedLayout('grid')}
                className={`px-2 sm:px-4 py-1.5 sm:py-2 text-sm sm:text-base rounded transition-colors ${
                  selectedLayout === 'grid'
                    ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                    : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
                }`}
              >
                <span className="hidden sm:inline">Grid View</span>
                <span className="sm:hidden">Grid</span>
              </button>
              <button
                onClick={() => setSelectedLayout('single')}
                className={`px-2 sm:px-4 py-1.5 sm:py-2 text-sm sm:text-base rounded transition-colors ${
                  selectedLayout === 'single'
                    ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                    : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
                }`}
              >
                <span className="hidden sm:inline">Single View</span>
                <span className="sm:hidden">Single</span>
              </button>
            </div>
          </div>
        </div>

        {/* Camera Selector for Single View */}
        {selectedLayout === 'single' && cameras.length > 1 && (
          <div className="mt-4 flex flex-col sm:flex-row sm:items-center gap-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Select Camera:</label>
            <select
              value={selectedCamera || ''}
              onChange={(e) => setSelectedCamera(parseInt(e.target.value))}
              className="block w-full sm:w-48 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              {cameras.map((camera) => (
                <option key={camera.id} value={camera.id}>
                  {camera.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Camera Feeds */}
      {selectedLayout === 'grid' ? (
        <div className={`grid gap-4 ${
          cameras.length === 1 ? 'grid-cols-1' : 
          cameras.length === 2 ? 'grid-cols-1 sm:grid-cols-2' : 
          'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'
        }`}>
          {cameras.map((camera) => (
            <CameraFeed
              key={camera.id}
              cameraId={camera.id}
              cameraName={camera.name}
              className="aspect-video"
            />
          ))}
        </div>
      ) : (
        <div className="max-w-4xl mx-auto">
          {selectedCamera && (
            <CameraFeed
              cameraId={selectedCamera}
              cameraName={cameras.find(c => c.id === selectedCamera)?.name || 'Camera'}
              className="aspect-video"
            />
          )}
        </div>
      )}
    </div>
  );
};

export default LiveFeeds;