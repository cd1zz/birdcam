import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type MotionSettings } from '../api/client';

const Settings: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'motion' | 'broadcast'>('motion');

  const { data: motionSettings, isLoading } = useQuery({
    queryKey: ['motionSettings'],
    queryFn: async () => {
      const response = await api.motion.getSettings();
      return response.data;
    },
  });

  const { data: broadcastConfig } = useQuery({
    queryKey: ['broadcastConfig'],
    queryFn: async () => {
      const response = await api.motion.getBroadcasterConfig();
      return response.data;
    },
  });

  const updateMotionMutation = useMutation({
    mutationFn: (settings: Partial<MotionSettings>) => api.motion.updateSettings(settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['motionSettings'] });
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
              Motion Detection
            </button>
            <button
              onClick={() => setActiveTab('broadcast')}
              className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                activeTab === 'broadcast'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Cross-Camera Broadcast
            </button>
          </nav>
        </div>
      </div>

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
                min="10"
                max="100"
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
                  Minimum Area
                </label>
                <input
                  type="number"
                  value={motionSettings.min_area}
                  onChange={(e) => handleMotionSettingChange('min_area', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Maximum Area
                </label>
                <input
                  type="number"
                  value={motionSettings.max_area}
                  onChange={(e) => handleMotionSettingChange('max_area', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Pre-Capture Seconds
                </label>
                <input
                  type="number"
                  value={motionSettings.pre_capture_seconds}
                  onChange={(e) => handleMotionSettingChange('pre_capture_seconds', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Post-Capture Seconds
                </label>
                <input
                  type="number"
                  value={motionSettings.post_capture_seconds}
                  onChange={(e) => handleMotionSettingChange('post_capture_seconds', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Motion Timeout (seconds)
              </label>
              <input
                type="number"
                value={motionSettings.motion_timeout}
                onChange={(e) => handleMotionSettingChange('motion_timeout', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="text-sm text-gray-500 mt-1">
                Minimum time between motion events
              </p>
            </div>

            {/* Motion Regions */}
            {motionSettings.regions && motionSettings.regions.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-900 mb-3">Motion Regions</h4>
                <div className="space-y-2">
                  {motionSettings.regions.map((region) => (
                    <div key={region.id} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                      <span className="font-medium">{region.name}</span>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={region.enabled}
                          onChange={(e) => {
                            const updatedRegions = motionSettings.regions.map(r =>
                              r.id === region.id ? { ...r, enabled: e.target.checked } : r
                            );
                            handleMotionSettingChange('regions', updatedRegions);
                          }}
                          className="mr-2"
                        />
                        <span className="text-sm text-gray-600">Enabled</span>
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {updateMotionMutation.isSuccess && (
            <div className="mt-4 p-3 bg-green-50 text-green-800 rounded">
              Settings updated successfully!
            </div>
          )}
        </div>
      )}

      {/* Broadcast Settings */}
      {activeTab === 'broadcast' && broadcastConfig && (
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-6">Cross-Camera Broadcast Settings</h3>
          
          <div className="space-y-4">
            <p className="text-gray-600">
              Configure how motion events from one camera trigger recording on other cameras.
            </p>
            
            <pre className="bg-gray-50 p-4 rounded overflow-auto text-sm">
              {JSON.stringify(broadcastConfig, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;