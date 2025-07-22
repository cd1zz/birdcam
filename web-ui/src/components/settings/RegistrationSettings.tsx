import { useQuery } from '@tanstack/react-query';
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

export default function RegistrationSettings() {
  const { data: settings, isLoading } = useQuery<RegistrationConfig>({
    queryKey: ['registration-settings'],
    queryFn: async () => {
      const response = await processingApi.get('/api/admin/settings/registration');
      return response.data;
    }
  });

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
        return 'text-green-600 dark:text-green-400';
      case 'invitation':
        return 'text-blue-600 dark:text-blue-400';
      case 'disabled':
        return 'text-red-600 dark:text-red-400';
      default:
        return '';
    }
  };

  return (
    <div className="space-y-6">
      {/* Registration Mode Section */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Registration Mode
        </h3>
        
        <div className="space-y-4">
          <div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Current Mode: </span>
            <span className={`text-sm font-semibold ${getModeColor(settings?.registration_mode || '')}`}>
              {settings?.registration_mode.toUpperCase()}
            </span>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {getModeDescription(settings?.registration_mode || '')}
          </p>
          
          <div className="space-y-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Allow resend verification email
              </span>
              <span className={`text-sm font-medium ${settings?.allow_resend_verification ? 'text-green-600' : 'text-gray-400'}`}>
                {settings?.allow_resend_verification ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Auto-delete unverified accounts after
              </span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                {settings?.auto_delete_unverified_days} days
              </span>
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
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {settings?.password_min_length} characters
            </span>
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
                <div className="flex items-center">
                  {settings?.[key as keyof RegistrationConfig] ? (
                    <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Configuration Note */}
      <div className="bg-blue-50 dark:bg-blue-900/50 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-blue-700 dark:text-blue-200">
              These settings are configured in your .env file. To change them, update the configuration and restart the server.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}