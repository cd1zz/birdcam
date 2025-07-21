import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type MotionSettings, type SystemSettings, type Camera } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import InteractiveCameraFeed from '../components/InteractiveCameraFeed';
import UserManagement from '../components/UserManagement';
import LogViewer from '../components/LogViewer';

const Settings: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'motion' | 'regions' | 'broadcast' | 'system' | 'users' | 'logs'>('motion');
  const [selectedCamera, setSelectedCamera] = useState<number>(0);
  const [warningMessage, setWarningMessage] = useState<string>('');
  const [localStoragePath, setLocalStoragePath] = useState<string>('');
  const [hasStorageChanges, setHasStorageChanges] = useState<boolean>(false);

  const { data: cameras } = useQuery({
    queryKey: ['cameras'],
    queryFn: api.cameras.list,
  });

  const { data: motionSettings, isLoading } = useQuery({
    queryKey: ['motionSettings', selectedCamera],
    queryFn: () => api.motion.getSettings(selectedCamera),
  });

  const { data: activePassiveConfig } = useQuery({
    queryKey: ['activePassiveConfig'],
    queryFn: api.motion.getActivePassiveConfig,
  });

  const { data: systemSettings } = useQuery({
    queryKey: ['systemSettings'],
    queryFn: api.system.getSettings,
  });

  const updateMotionMutation = useMutation({
    mutationFn: (settings: Partial<MotionSettings>) => api.motion.updateSettings(settings, selectedCamera),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['motionSettings', selectedCamera] });
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


  const handleMotionSettingChange = (key: keyof MotionSettings, value: number | boolean) => {
    if (motionSettings) {
      updateMotionMutation.mutate({ [key]: value });
    }
  };

  const handleSystemSettingChange = (category: keyof SystemSettings, key: string, value: string | number) => {
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

  const handleClassToggle = (className: string, enabled: boolean) => {
    if (systemSettings) {
      const newClasses = enabled 
        ? [...systemSettings.detection.classes, className]
        : systemSettings.detection.classes.filter(c => c !== className);
      updateSystemMutation.mutate({ 
        detection: { 
          ...systemSettings.detection,
          classes: newClasses 
        } 
      });
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
              <span className="hidden sm:inline">Motion Settings</span>
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
              <span className="hidden sm:inline">Active-Passive Mode</span>
              <span className="sm:hidden">A-P Mode</span>
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
            {user?.role === 'admin' && (
              <>
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
              </>
            )}
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

      {/* Camera Selector - Only show for camera-related tabs */}
      {cameras && cameras.length > 1 && (activeTab === 'motion' || activeTab === 'regions' || activeTab === 'broadcast') && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Configure Camera:</label>
            <select
              value={selectedCamera}
              onChange={(e) => setSelectedCamera(parseInt(e.target.value))}
              className="block w-full sm:w-48 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              {cameras.map((camera: Camera) => (
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
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-6 text-gray-900 dark:text-white">Motion Detection Settings</h3>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
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
              <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400 mt-1">
                <span>Less Sensitive</span>
                <span>{motionSettings.motion_threshold}</span>
                <span>More Sensitive</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Minimum Contour Area
                </label>
                <input
                  type="number"
                  value={motionSettings.min_contour_area}
                  onChange={(e) => handleMotionSettingChange('min_contour_area', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Motion Timeout (seconds)
                </label>
                <input
                  type="number"
                  value={motionSettings.motion_timeout_seconds}
                  onChange={(e) => handleMotionSettingChange('motion_timeout_seconds', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
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
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Enable Motion Box Detection</span>
              </label>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Use the Motion Regions tab to visually configure the detection area
              </p>
            </div>
          </div>

          {updateMotionMutation.isSuccess && (
            <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300 rounded">
              Settings updated successfully!
            </div>
          )}
        </div>
      )}

      {/* Motion Regions Tab */}
      {activeTab === 'regions' && cameras && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-6 text-gray-900 dark:text-white">Configure Motion Detection Area</h3>
          
          <div className="space-y-4">
            <p className="text-gray-600 dark:text-gray-300">
              Use the controls on the camera feed to draw and adjust the motion detection box. 
              Motion outside this area will be ignored.
            </p>
            
            <div className="aspect-video max-w-2xl">
              <InteractiveCameraFeed
                cameraId={selectedCamera}
                cameraName={cameras.find((c: Camera) => c.id === selectedCamera)?.name || `Camera ${selectedCamera}`}
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
                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Motion Box Coordinates</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Top-Left: ({motionSettings.motion_box_x1}, {motionSettings.motion_box_y1})
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Bottom-Right: ({motionSettings.motion_box_x2}, {motionSettings.motion_box_y2})
                  </p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Detection Status</p>
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
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-6 text-gray-900 dark:text-white">Active-Passive Camera Settings</h3>
          
          <div className="space-y-4">
            <p className="text-gray-600 dark:text-gray-300">
              In active-passive mode, Camera 0 detects motion and triggers recording on all cameras.
            </p>
            
            <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded">
              <h4 className="font-medium text-blue-900 dark:text-blue-200 mb-2">How it works:</h4>
              <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1">
                <li>• Camera 0 is the <strong>active camera</strong> - detects motion</li>
                <li>• Other cameras are <strong>passive cameras</strong> - record when triggered</li>
                <li>• Configure motion detection box only on Camera 0</li>
                <li>• All cameras save separate recording files</li>
              </ul>
            </div>
            
            <pre className="bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white p-4 rounded overflow-auto text-sm">
              {JSON.stringify(activePassiveConfig, null, 2)}
            </pre>
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
                <div className="grid grid-cols-3 gap-3">
                  {['bird', 'cat', 'dog', 'person', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe'].map((className) => (
                    <label key={className} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={systemSettings.detection.classes.includes(className)}
                        onChange={(e) => handleClassToggle(className, e.target.checked)}
                        className="mr-2"
                      />
                      <span className="text-sm capitalize text-gray-900 dark:text-white">{className}</span>
                    </label>
                  ))}
                </div>
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
                  >
                    <option value="yolov5n">YOLOv5 Nano (fastest)</option>
                    <option value="yolov5s">YOLOv5 Small</option>
                    <option value="yolov5m">YOLOv5 Medium</option>
                    <option value="yolov5l">YOLOv5 Large</option>
                    <option value="yolov5x">YOLOv5 XLarge (most accurate)</option>
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

      {/* Logs Tab */}
      {activeTab === 'logs' && user?.role === 'admin' && (
        <LogViewer />
      )}
    </div>
  );
};

export default Settings;