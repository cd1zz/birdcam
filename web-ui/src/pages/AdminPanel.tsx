import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type SystemSettings, type MotionSettings, type Camera } from '../api/client';
import InteractiveCameraFeed from '../components/InteractiveCameraFeed';
import UserManagement from '../components/UserManagement';
import LogViewer from '../components/LogViewer';
import EmailSettings from '../components/settings/EmailSettings';
import RegistrationSettings from '../components/settings/RegistrationSettings';
import RegistrationManagement from '../components/settings/RegistrationManagement';
import EmailTemplates from '../components/settings/EmailTemplates';
import ClassSelector from '../components/settings/ClassSelector';

const AdminPanel: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'motion' | 'regions' | 'broadcast' | 'system' | 'users' | 'email' | 'registration' | 'logs'>('motion');
  const [warningMessage, setWarningMessage] = useState<string>('');
  const [localStoragePath, setLocalStoragePath] = useState<string>('');
  const [hasStorageChanges, setHasStorageChanges] = useState<boolean>(false);
  const [accessDenied] = useState<boolean>(false);
  const [selectedCameraId, setSelectedCameraId] = useState<number>(0);

  const { data: motionSettings } = useQuery({
    queryKey: ['motionSettings', selectedCameraId],
    queryFn: () => api.motion.getSettings(selectedCameraId),
  });

  const { data: cameras } = useQuery({
    queryKey: ['cameras'],
    queryFn: api.cameras.list,
  });

  const { data: systemSettings } = useQuery({
    queryKey: ['systemSettings'],
    queryFn: api.system.getSettings,
  });

  const { data: availableModels } = useQuery({
    queryKey: ['availableModels'],
    queryFn: api.models.getAvailable,
  });


  const updateMotionMutation = useMutation({
    mutationFn: (settings: Partial<MotionSettings>) => 
      api.motion.updateSettings(settings, selectedCameraId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['motionSettings', selectedCameraId] });
    },
  });

  const updateSystemMutation = useMutation({
    mutationFn: (settings: Partial<SystemSettings>) => api.system.updateSettings(settings),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['systemSettings'] });
      if (result.warning) {
        setWarningMessage(result.warning);
        setTimeout(() => setWarningMessage(''), 10000); // Clear after 10 seconds
      }
      // Reset storage changes flag after successful save
      setHasStorageChanges(false);
    },
  });

  // Effect to sync local storage path with system settings
  React.useEffect(() => {
    if (systemSettings?.storage?.storage_path) {
      if (!hasStorageChanges || localStoragePath === '') {
        setLocalStoragePath(systemSettings.storage.storage_path);
      }
    }
  }, [systemSettings, hasStorageChanges, localStoragePath]);



  const handleSystemSettingChange = (category: keyof SystemSettings, key: string, value: string | number | string[]) => {
    if (systemSettings) {
      updateSystemMutation.mutate({ 
        [category]: { 
          ...systemSettings[category],
          [key]: value 
        } 
      });
    }
  };

  const handleConfidenceChange = (className: string, value: number) => {
    if (systemSettings) {
      const newConfidences = { ...systemSettings.detection.confidences, [className]: value };
      updateSystemMutation.mutate({ 
        detection: { 
          ...systemSettings.detection,
          confidences: newConfidences 
        } 
      });
    }
  };

  const handleMotionSettingChange = (key: keyof MotionSettings, value: number | boolean) => {
    if (motionSettings) {
      updateMotionMutation.mutate({ 
        ...motionSettings,  // Include all existing settings
        [key]: value 
      });
    }
  };

  const handleMotionRegionChange = (region: { x1: number; y1: number; x2: number; y2: number; enabled: boolean }) => {
    if (motionSettings) {
      updateMotionMutation.mutate({
        ...motionSettings,  // Include all existing settings
        motion_box_enabled: region.enabled,
        motion_box_x1: Math.round(region.x1),
        motion_box_y1: Math.round(region.y1),
        motion_box_x2: Math.round(region.x2),
        motion_box_y2: Math.round(region.y2),
      });
    }
  };



  if (accessDenied) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-8">
        <div className="max-w-2xl mx-auto text-center">
          <div className="text-6xl mb-4">🚫</div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Access Denied</h2>
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            The Admin Panel can only be accessed from internal network IP addresses.
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Please connect from your local network to access administrative functions.
          </p>
        </div>
      </div>
    );
  }


  return (
    <div>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm mb-6 p-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Admin Panel</h2>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          Configure system settings and manage users. This panel is only accessible from internal network IP addresses.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm mb-6">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex overflow-x-auto scrollbar-hide">
            <button
              onClick={() => setActiveTab('motion')}
              className={`px-3 sm:px-6 py-2 sm:py-3 font-medium text-xs sm:text-sm border-b-2 transition-colors whitespace-nowrap ${
                activeTab === 'motion'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
              }`}
            >
              <span className="hidden sm:inline">Motion Detection</span>
              <span className="sm:hidden">Motion</span>
            </button>
            <button
              onClick={() => setActiveTab('regions')}
              className={`px-3 sm:px-6 py-2 sm:py-3 font-medium text-xs sm:text-sm border-b-2 transition-colors whitespace-nowrap ${
                activeTab === 'regions'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
              }`}
            >
              <span className="hidden sm:inline">Motion Regions</span>
              <span className="sm:hidden">Regions</span>
            </button>
            <button
              onClick={() => setActiveTab('broadcast')}
              className={`px-3 sm:px-6 py-2 sm:py-3 font-medium text-xs sm:text-sm border-b-2 transition-colors whitespace-nowrap ${
                activeTab === 'broadcast'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
              }`}
            >
              <span className="hidden sm:inline">Active-Passive</span>
              <span className="sm:hidden">Broadcast</span>
            </button>
            <button
              onClick={() => setActiveTab('system')}
              className={`px-3 sm:px-6 py-2 sm:py-3 font-medium text-xs sm:text-sm border-b-2 transition-colors whitespace-nowrap ${
                activeTab === 'system'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
              }`}
            >
              <span className="hidden sm:inline">System Settings</span>
              <span className="sm:hidden">System</span>
            </button>
            <button
              onClick={() => setActiveTab('users')}
              className={`px-3 sm:px-6 py-2 sm:py-3 font-medium text-xs sm:text-sm border-b-2 transition-colors whitespace-nowrap ${
                activeTab === 'users'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
              }`}
            >
              <span className="hidden sm:inline">Users</span>
              <span className="sm:hidden">Users</span>
            </button>
            <button
              onClick={() => setActiveTab('email')}
              className={`px-3 sm:px-6 py-2 sm:py-3 font-medium text-xs sm:text-sm border-b-2 transition-colors whitespace-nowrap ${
                activeTab === 'email'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
              }`}
            >
              <span className="hidden sm:inline">Email</span>
              <span className="sm:hidden">Email</span>
            </button>
            <button
              onClick={() => setActiveTab('registration')}
              className={`px-3 sm:px-6 py-2 sm:py-3 font-medium text-xs sm:text-sm border-b-2 transition-colors whitespace-nowrap ${
                activeTab === 'registration'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
              }`}
            >
              <span className="hidden sm:inline">Registration</span>
              <span className="sm:hidden">Reg</span>
            </button>
            <button
              onClick={() => setActiveTab('logs')}
              className={`px-3 sm:px-6 py-2 sm:py-3 font-medium text-xs sm:text-sm border-b-2 transition-colors whitespace-nowrap ${
                activeTab === 'logs'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
              }`}
            >
              <span className="hidden sm:inline">System Logs</span>
              <span className="sm:hidden">Logs</span>
            </button>
          </nav>
        </div>
      </div>

      {/* Warning Message */}
      {warningMessage && (
        <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4 mb-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-orange-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-orange-700 dark:text-orange-300">{warningMessage}</p>
            </div>
          </div>
        </div>
      )}



      {/* Motion Detection Settings */}
      {activeTab === 'motion' && motionSettings && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-6 text-gray-900 dark:text-white">Motion Detection Settings</h3>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Motion Sensitivity (Lower = More Sensitive)
              </label>
              <div className="flex items-center space-x-4">
                <input
                  type="range"
                  min="1000"
                  max="20000"
                  step="500"
                  value={motionSettings.motion_threshold}
                  onChange={(e) => handleMotionSettingChange('motion_threshold', parseInt(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm w-16 text-gray-900 dark:text-white">{motionSettings.motion_threshold}</span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Threshold for motion detection trigger</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Minimum Motion Area
              </label>
              <div className="flex items-center space-x-4">
                <input
                  type="range"
                  min="100"
                  max="5000"
                  step="100"
                  value={motionSettings.min_contour_area}
                  onChange={(e) => handleMotionSettingChange('min_contour_area', parseInt(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm w-16 text-gray-900 dark:text-white">{motionSettings.min_contour_area}</span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Minimum area to consider as motion (pixels)</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Motion Timeout (seconds)
              </label>
              <input
                type="number"
                min="5"
                max="300"
                value={motionSettings.motion_timeout_seconds}
                onChange={(e) => handleMotionSettingChange('motion_timeout_seconds', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Stop recording after no motion for this duration</p>
            </div>
          </div>

          {updateMotionMutation.isSuccess && (
            <div className="mt-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
              <p className="text-sm text-green-700 dark:text-green-300">Motion settings updated successfully!</p>
            </div>
          )}
        </div>
      )}

      {/* Motion Regions Tab */}
      {activeTab === 'regions' && (
        <div className="space-y-6">
          {/* Camera Selection */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Select Camera</h3>
            <div className="flex gap-2">
              {cameras?.map((camera: Camera) => (
                <button
                  key={camera.id}
                  onClick={() => setSelectedCameraId(camera.id)}
                  className={`px-4 py-2 rounded-md transition-colors ${
                    selectedCameraId === camera.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                  }`}
                >
                  {camera.name}
                </button>
              ))}
            </div>
          </div>

          {/* Interactive Camera Feed */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Define Motion Detection Region
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Click and drag on the camera feed to define the area where motion should be detected.
            </p>
            
            {motionSettings && (
              <InteractiveCameraFeed
                cameraId={selectedCameraId}
                cameraName={cameras?.find(c => c.id === selectedCameraId)?.name || `Camera ${selectedCameraId}`}
                showMotionBox={true}
                onMotionBoxChange={(box) => handleMotionRegionChange({
                  x1: box.x1,
                  y1: box.y1,
                  x2: box.x2,
                  y2: box.y2,
                  enabled: box.enabled
                })}
              />
            )}
          </div>
        </div>
      )}

      {/* Active-Passive Settings */}
      {activeTab === 'broadcast' && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-6 text-gray-900 dark:text-white">Active-Passive Camera Configuration</h3>
          
          <div className="space-y-4">
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">How Active-Passive Mode Works</h4>
              <p className="text-sm text-blue-700 dark:text-blue-300">
                In active-passive mode, Camera 0 monitors for motion while Camera 1 remains in standby. 
                When motion is detected on Camera 0, both cameras start recording simultaneously, 
                capturing the event from multiple angles.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">Active Camera</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">Camera 0 (Primary)</p>
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">Continuously monitors for motion</p>
              </div>
              
              <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">Passive Camera</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">Camera 1 (Secondary)</p>
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">Records when triggered by active camera</p>
              </div>
            </div>

            <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
              <p className="text-sm text-gray-700 dark:text-gray-300">
                <strong>Note:</strong> This mode is automatically enabled when exactly 2 cameras are connected. 
                The system will use Camera 0 as the active camera and Camera 1 as the passive camera.
              </p>
            </div>
          </div>
        </div>
      )}


      {/* System Settings */}
      {activeTab === 'system' && systemSettings && (
        <div className="space-y-6">
          {/* Storage Configuration */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-6 text-gray-900 dark:text-white">Storage Configuration</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Storage Path
                </label>
                <input
                  type="text"
                  value={localStoragePath}
                  onChange={(e) => {
                    setLocalStoragePath(e.target.value);
                    setHasStorageChanges(e.target.value !== systemSettings.storage.storage_path);
                  }}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="/path/to/storage"
                />
                <p className="text-sm text-orange-600 dark:text-orange-400 mt-1">
                  ⚠️ Changing storage path requires service restart. Existing files will remain in the old location.
                </p>
              </div>
              
              {/* Save button - only show when there are changes */}
              {hasStorageChanges && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-amber-600 dark:text-amber-400">
                    You have unsaved changes
                  </p>
                  <div className="space-x-3">
                    <button
                      onClick={() => {
                        setLocalStoragePath(systemSettings.storage.storage_path);
                        setHasStorageChanges(false);
                      }}
                      className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => {
                        // Basic path validation
                        const trimmedPath = localStoragePath.trim();
                        if (!trimmedPath) {
                          alert('Storage path cannot be empty');
                          return;
                        }
                        if (!trimmedPath.startsWith('/')) {
                          alert('Storage path must be an absolute path (starting with /)');
                          return;
                        }
                        handleSystemSettingChange('storage', 'storage_path', trimmedPath);
                      }}
                      disabled={updateSystemMutation.isPending}
                      className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {updateSystemMutation.isPending ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Detection Settings */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-6 text-gray-900 dark:text-white">Detection Configuration</h3>
            
            <div className="space-y-6">
              {/* Available Classes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Enabled Detection Classes
                </label>
                <ClassSelector
                  modelId={systemSettings.detection.model_name}
                  selectedClasses={systemSettings.detection.classes}
                  onChange={(classes) => handleSystemSettingChange('detection', 'classes', classes)}
                  disabled={false}
                />
              </div>

              {/* Confidence Thresholds */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Confidence Thresholds
                </label>
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(systemSettings.detection.confidences).map(([className, confidence]) => (
                    <div key={className}>
                      <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1 capitalize">
                        {className === 'default' ? 'Default Confidence' : `${className} Confidence`}
                      </label>
                      <div className="flex items-center space-x-2">
                        <input
                          type="range"
                          min="0.1"
                          max="0.9"
                          step="0.05"
                          value={confidence}
                          onChange={(e) => handleConfidenceChange(className, parseFloat(e.target.value))}
                          className="flex-1"
                        />
                        <span className="text-sm w-12 text-gray-900 dark:text-white">{confidence.toFixed(2)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Model Settings */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    YOLO Model
                  </label>
                  <select
                    value={systemSettings.detection.model_name}
                    onChange={(e) => handleSystemSettingChange('detection', 'model_name', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    disabled={!availableModels}
                  >
                    {!availableModels ? (
                      <option>Loading models...</option>
                    ) : (
                      availableModels.models.map((model) => (
                        <option key={model.id} value={model.id}>
                          {model.name} - {model.description}
                        </option>
                      ))
                    )}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Process Every Nth Frame
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={systemSettings.detection.process_every_nth_frame}
                    onChange={(e) => handleSystemSettingChange('detection', 'process_every_nth_frame', parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Higher = faster processing, lower accuracy</p>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Max Thumbnails Per Video
                </label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={systemSettings.detection.max_thumbnails_per_video}
                  onChange={(e) => handleSystemSettingChange('detection', 'max_thumbnails_per_video', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Retention Policies */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-6 text-gray-900 dark:text-white">Retention Policies</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Detection Retention (days)
                </label>
                <input
                  type="number"
                  min="1"
                  max="365"
                  value={systemSettings.retention.detection_retention_days}
                  onChange={(e) => handleSystemSettingChange('retention', 'detection_retention_days', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">How long to keep videos with detections</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  No Detection Retention (days)
                </label>
                <input
                  type="number"
                  min="1"
                  max="90"
                  value={systemSettings.retention.no_detection_retention_days}
                  onChange={(e) => handleSystemSettingChange('retention', 'no_detection_retention_days', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">How long to keep videos without detections</p>
              </div>
            </div>
          </div>

          {/* Sync Settings */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-6 text-gray-900 dark:text-white">Sync & Performance</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Sync Interval (minutes)
                </label>
                <input
                  type="number"
                  min="1"
                  max="120"
                  value={systemSettings.sync.sync_interval_minutes}
                  onChange={(e) => handleSystemSettingChange('sync', 'sync_interval_minutes', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">How often Pi syncs to processing server</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Upload Timeout (seconds)
                </label>
                <input
                  type="number"
                  min="30"
                  max="1800"
                  value={systemSettings.sync.upload_timeout_seconds}
                  onChange={(e) => handleSystemSettingChange('sync', 'upload_timeout_seconds', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Timeout for file uploads</p>
              </div>
            </div>
          </div>

          {updateSystemMutation.isSuccess && !warningMessage && (
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-green-700 dark:text-green-300">System settings updated successfully!</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <UserManagement />
      )}

      {/* Email Settings Tab */}
      {activeTab === 'email' && (
        <EmailSettings />
      )}

      {/* Registration Tab */}
      {activeTab === 'registration' && (
        <div className="space-y-6">
          <RegistrationSettings />
          <RegistrationManagement />
          <EmailTemplates />
        </div>
      )}

      {/* Logs Tab */}
      {activeTab === 'logs' && (
        <LogViewer />
      )}
    </div>
  );
};

export default AdminPanel;