import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type MotionSettings } from '../api/client';
import InteractiveCameraFeed from '../components/InteractiveCameraFeed';

const Settings: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'motion' | 'regions' | 'broadcast'>('motion');
  const [selectedCamera, setSelectedCamera] = useState<number>(0);

  const { data: cameras } = useQuery({
    queryKey: ['cameras'],
    queryFn: async () => {
      const response = await api.cameras.list();
      return response.data.cameras;
    },
  });

  const { data: motionSettings, isLoading } = useQuery({
    queryKey: ['motionSettings', selectedCamera],
    queryFn: async () => {
      const response = await api.motion.getSettings(selectedCamera);
      return response.data;
    },
  });

  const { data: activePassiveConfig } = useQuery({
    queryKey: ['activePassiveConfig'],
    queryFn: async () => {
      const response = await api.motion.getActivePassiveConfig();
      return response.data;
    },
  });

  const updateMotionMutation = useMutation({
    mutationFn: (settings: Partial<MotionSettings>) => api.motion.updateSettings(settings, selectedCamera),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['motionSettings', selectedCamera] });
    },
  });


  const handleMotionSettingChange = (key: keyof MotionSettings, value: any) => {
    if (motionSettings) {
      updateMotionMutation.mutate({ [key]: value });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div>
      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow-sm mb-6">
        <div className="border-b">
          <nav className="flex">
            <button
              onClick={() => setActiveTab('motion')}
              className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                activeTab === 'motion'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Motion Settings
            </button>
            <button
              onClick={() => setActiveTab('regions')}
              className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                activeTab === 'regions'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Motion Regions
            </button>
            <button
              onClick={() => setActiveTab('broadcast')}
              className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                activeTab === 'broadcast'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Active-Passive Mode
            </button>
          </nav>
        </div>
      </div>

      {/* Camera Selector */}
      {cameras && cameras.length > 1 && (
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-gray-700">Configure Camera:</label>
            <select
              value={selectedCamera}
              onChange={(e) => setSelectedCamera(parseInt(e.target.value))}
              className="block w-48 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              {cameras.map((camera) => (
                <option key={camera.id} value={camera.id}>
                  {camera.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Motion Detection Settings */}
      {activeTab === 'motion' && motionSettings && (
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-6">Motion Detection Settings</h3>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Motion Threshold
              </label>
              <input
                type="range"
                min="1000"
                max="10000"
                value={motionSettings.motion_threshold}
                onChange={(e) => handleMotionSettingChange('motion_threshold', parseInt(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-sm text-gray-500 mt-1">
                <span>Less Sensitive</span>
                <span>{motionSettings.motion_threshold}</span>
                <span>More Sensitive</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Minimum Contour Area
                </label>
                <input
                  type="number"
                  value={motionSettings.min_contour_area}
                  onChange={(e) => handleMotionSettingChange('min_contour_area', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Motion Timeout (seconds)
                </label>
                <input
                  type="number"
                  value={motionSettings.motion_timeout_seconds}
                  onChange={(e) => handleMotionSettingChange('motion_timeout_seconds', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={motionSettings.motion_box_enabled}
                  onChange={(e) => handleMotionSettingChange('motion_box_enabled', e.target.checked)}
                  className="mr-2"
                />
                <span className="text-sm font-medium text-gray-700">Enable Motion Box Detection</span>
              </label>
              <p className="text-sm text-gray-500 mt-1">
                Use the Motion Regions tab to visually configure the detection area
              </p>
            </div>
          </div>

          {updateMotionMutation.isSuccess && (
            <div className="mt-4 p-3 bg-green-50 text-green-800 rounded">
              Settings updated successfully!
            </div>
          )}
        </div>
      )}

      {/* Motion Regions Tab */}
      {activeTab === 'regions' && cameras && (
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-6">Configure Motion Detection Area</h3>
          
          <div className="space-y-4">
            <p className="text-gray-600">
              Use the controls on the camera feed to draw and adjust the motion detection box. 
              Motion outside this area will be ignored.
            </p>
            
            <div className="aspect-video max-w-2xl">
              <InteractiveCameraFeed
                cameraId={selectedCamera}
                cameraName={cameras.find(c => c.id === selectedCamera)?.name || `Camera ${selectedCamera}`}
                className="w-full h-full"
                showMotionBox={true}
                onMotionBoxChange={(box) => {
                  console.log('Motion box changed:', box);
                  queryClient.invalidateQueries({ queryKey: ['motionSettings', selectedCamera] });
                }}
              />
            </div>
            
            {motionSettings && (
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div className="bg-gray-50 p-3 rounded">
                  <p className="text-sm font-medium text-gray-700">Motion Box Coordinates</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Top-Left: ({motionSettings.motion_box_x1}, {motionSettings.motion_box_y1})
                  </p>
                  <p className="text-xs text-gray-500">
                    Bottom-Right: ({motionSettings.motion_box_x2}, {motionSettings.motion_box_y2})
                  </p>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <p className="text-sm font-medium text-gray-700">Detection Status</p>
                  <p className={`text-xs mt-1 ${motionSettings.motion_box_enabled ? 'text-green-600' : 'text-red-600'}`}>
                    {motionSettings.motion_box_enabled ? 'Enabled' : 'Disabled'}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Active-Passive Settings */}
      {activeTab === 'broadcast' && activePassiveConfig && (
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-6">Active-Passive Camera Settings</h3>
          
          <div className="space-y-4">
            <p className="text-gray-600">
              In active-passive mode, Camera 0 detects motion and triggers recording on all cameras.
            </p>
            
            <div className="bg-blue-50 p-4 rounded">
              <h4 className="font-medium text-blue-900 mb-2">How it works:</h4>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• Camera 0 is the <strong>active camera</strong> - detects motion</li>
                <li>• Other cameras are <strong>passive cameras</strong> - record when triggered</li>
                <li>• Configure motion detection box only on Camera 0</li>
                <li>• All cameras save separate recording files</li>
              </ul>
            </div>
            
            <pre className="bg-gray-50 p-4 rounded overflow-auto text-sm">
              {JSON.stringify(activePassiveConfig, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;