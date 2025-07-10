import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import CameraFeed from '../components/CameraFeed';
import { api } from '../api/client';

const LiveFeeds: React.FC = () => {
  const [selectedLayout, setSelectedLayout] = useState<'grid' | 'single'>('grid');
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null);

  const { data: cameras, isLoading, error } = useQuery({
    queryKey: ['cameras'],
    queryFn: async () => {
      const response = await api.cameras.list();
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
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
          <p className="mt-4 text-gray-600">Loading cameras...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Failed to load cameras. Please check your connection.</p>
      </div>
    );
  }

  if (!cameras || cameras.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-yellow-800">No cameras found. Please check your camera configuration.</p>
      </div>
    );
  }

  return (
    <div>
      {/* Controls */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Camera Feeds</h3>
            <p className="text-sm text-gray-500">{cameras.length} camera{cameras.length > 1 ? 's' : ''} active</p>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Layout Toggle */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setSelectedLayout('grid')}
                className={`px-4 py-2 rounded transition-colors ${
                  selectedLayout === 'grid'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Grid View
              </button>
              <button
                onClick={() => setSelectedLayout('single')}
                className={`px-4 py-2 rounded transition-colors ${
                  selectedLayout === 'single'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Single View
              </button>
            </div>
          </div>
        </div>

        {/* Camera Selector for Single View */}
        {selectedLayout === 'single' && cameras.length > 1 && (
          <div className="mt-4 flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Select Camera:</label>
            <select
              value={selectedCamera || ''}
              onChange={(e) => setSelectedCamera(e.target.value)}
              className="block w-48 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
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
          cameras.length === 2 ? 'grid-cols-2' : 
          'grid-cols-2 lg:grid-cols-3'
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