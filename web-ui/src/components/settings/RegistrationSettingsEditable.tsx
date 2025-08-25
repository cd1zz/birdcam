import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { processingApi } from '../../api/client';

interface RegistrationConfig {
  registration_mode: 'open' | 'invitation' | 'disabled';
  allow_resend_verification: boolean;
  auto_delete_unverified_days: number;
  password_min_length: number;
  password_require_uppercase: boolean;
  password_require_lowercase: boolean;
  password_require_numbers: boolean;
  password_require_special: boolean;
}

export default function RegistrationSettingsEditable() {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<RegistrationConfig | null>(null);

  const { data: settings, isLoading } = useQuery<RegistrationConfig>({
    queryKey: ['registration-settings'],
    queryFn: async () => {
      const response = await processingApi.get('/api/admin/settings/registration');
      return response.data;
    }
  });

  // Update registration settings
  const updateSettingsMutation = useMutation({
    mutationFn: async (data: Partial<RegistrationConfig>) => {
      const response = await processingApi.put('/api/admin/settings/registration', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['registration-settings'] });
      setIsEditing(false);
      setEditForm(null);
    }
  });

  useEffect(() => {
    if (settings && !editForm && isEditing) {
      setEditForm(settings);
    }
  }, [settings, editForm, isEditing]);

  const handleSave = () => {
    if (editForm) {
      updateSettingsMutation.mutate(editForm);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditForm(null);
  };

  if (isLoading) {
    return <div className="animate-pulse">Loading registration settings...</div>;
  }

  const getModeDescription = (mode: string) => {
    switch (mode) {
      case 'open':
        return 'Anyone can register for an account';
      case 'invitation':
        return 'Registration requires an invitation link from an admin';
      case 'disabled':
        return 'New registrations are not allowed';
      default:
        return '';
    }
  };

  const getModeColor = (mode: string) => {
    switch (mode) {
      case 'open':
        return 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/50';
      case 'invitation':
        return 'text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/50';
      case 'disabled':
        return 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/50';
      default:
        return '';
    }
  };

  const currentSettings = editForm || settings;

  return (
    <div className="space-y-6">
      {/* Registration Mode Section */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Registration Settings
          </h3>
          {!isEditing ? (
            <button
              onClick={() => setIsEditing(true)}
              className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-indigo-700 bg-indigo-100 hover:bg-indigo-200 dark:bg-indigo-900 dark:text-indigo-200 dark:hover:bg-indigo-800"
            >
              Edit Settings
            </button>
          ) : (
            <div className="flex space-x-2">
              <button
                onClick={handleCancel}
                className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-xs font-medium rounded text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={updateSettingsMutation.isPending}
                className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
              >
                {updateSettingsMutation.isPending ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          )}
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Registration Mode
            </label>
            {!isEditing ? (
              <div>
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getModeColor(currentSettings?.registration_mode || '')}`}>
                  {currentSettings?.registration_mode.toUpperCase()}
                </span>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                  {getModeDescription(currentSettings?.registration_mode || '')}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {['disabled', 'invitation', 'open'].map((mode) => (
                  <label key={mode} className="flex items-start cursor-pointer">
                    <input
                      type="radio"
                      name="registration_mode"
                      value={mode}
                      checked={editForm?.registration_mode === mode}
                      onChange={(e) => setEditForm({ ...editForm!, registration_mode: e.target.value as 'open' | 'invitation' | 'disabled' })}
                      className="mt-0.5 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                    />
                    <div className="ml-3">
                      <span className="block text-sm font-medium text-gray-900 dark:text-white">
                        {mode.charAt(0).toUpperCase() + mode.slice(1)}
                      </span>
                      <span className="block text-sm text-gray-500 dark:text-gray-400">
                        {getModeDescription(mode)}
                      </span>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>
          
          <div className="space-y-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Allow resend verification email
              </span>
              {!isEditing ? (
                <span className={`text-sm font-medium ${currentSettings?.allow_resend_verification ? 'text-green-600' : 'text-gray-400'}`}>
                  {currentSettings?.allow_resend_verification ? 'Enabled' : 'Disabled'}
                </span>
              ) : (
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editForm?.allow_resend_verification || false}
                    onChange={(e) => setEditForm({ ...editForm!, allow_resend_verification: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 dark:peer-focus:ring-indigo-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-indigo-600"></div>
                </label>
              )}
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Auto-delete unverified accounts after
              </span>
              {!isEditing ? (
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {currentSettings?.auto_delete_unverified_days} days
                </span>
              ) : (
                <input
                  type="number"
                  min="1"
                  max="365"
                  value={editForm?.auto_delete_unverified_days || 7}
                  onChange={(e) => setEditForm({ ...editForm!, auto_delete_unverified_days: parseInt(e.target.value) || 7 })}
                  className="w-20 px-2 py-1 text-sm text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 rounded"
                />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Password Requirements Section */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Password Requirements
        </h3>
        
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Minimum length
            </span>
            {!isEditing ? (
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                {currentSettings?.password_min_length} characters
              </span>
            ) : (
              <input
                type="number"
                min="6"
                max="32"
                value={editForm?.password_min_length || 8}
                onChange={(e) => setEditForm({ ...editForm!, password_min_length: parseInt(e.target.value) || 8 })}
                className="w-20 px-2 py-1 text-sm text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 rounded"
              />
            )}
          </div>
          
          <div className="space-y-2 pt-3 border-t border-gray-200 dark:border-gray-700">
            {[
              { key: 'password_require_uppercase', label: 'Require uppercase letters' },
              { key: 'password_require_lowercase', label: 'Require lowercase letters' },
              { key: 'password_require_numbers', label: 'Require numbers' },
              { key: 'password_require_special', label: 'Require special characters' }
            ].map(({ key, label }) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {label}
                </span>
                {!isEditing ? (
                  <div className="flex items-center">
                    {currentSettings?.[key as keyof RegistrationConfig] ? (
                      <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    )}
                  </div>
                ) : (
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={editForm?.[key as keyof RegistrationConfig] as boolean || false}
                      onChange={(e) => setEditForm({ ...editForm!, [key]: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 dark:peer-focus:ring-indigo-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-indigo-600"></div>
                  </label>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Status Messages */}
      {updateSettingsMutation.isError && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700 dark:text-red-200">
                Failed to update registration settings. Please check the server logs.
              </p>
            </div>
          </div>
        </div>
      )}

      {updateSettingsMutation.isSuccess && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-green-700 dark:text-green-200">
                Registration settings updated successfully. Changes take effect immediately.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Configuration Note */}
      <div className="bg-amber-50 dark:bg-amber-900/50 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-amber-700 dark:text-amber-200">
              <strong>Note:</strong> These settings override any values in your .env file. The UI settings are stored in the database and take precedence.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}