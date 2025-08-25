import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { processingApi } from '../../api/client';

interface EmailConfig {
  email_provider: 'smtp' | 'azure';
  smtp_server: string;
  smtp_port: number;
  smtp_username: string;
  smtp_use_tls: boolean;
  smtp_use_ssl: boolean;
  azure_tenant_id: string;
  azure_client_id: string;
  azure_sender_email: string;
  azure_use_shared_mailbox: boolean;
  from_email: string;
  from_name: string;
  verification_subject: string;
  verification_expires_hours: number;
  is_configured: boolean;
  has_smtp_password: boolean;
  has_azure_secret: boolean;
}

export default function EmailSettings() {
  const queryClient = useQueryClient();
  const [testEmail, setTestEmail] = useState('');
  const [testStatus, setTestStatus] = useState<{type: 'success' | 'error', message: string} | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<Partial<EmailConfig>>({});
  const [smtpPassword, setSmtpPassword] = useState('');
  const [azureSecret, setAzureSecret] = useState('');

  const { data: settings, isLoading, error } = useQuery<EmailConfig>({
    queryKey: ['email-settings'],
    queryFn: async () => {
      const response = await processingApi.get('/api/admin/settings/email');
      return response.data;
    }
  });

  useEffect(() => {
    if (settings) {
      setFormData(settings);
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: async (data: Partial<EmailConfig> & { smtp_password?: string; azure_client_secret?: string }) => {
      const response = await processingApi.put('/api/admin/settings/email', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-settings'] });
      setIsEditing(false);
      setSmtpPassword('');
      setAzureSecret('');
      setTestStatus({ type: 'success', message: 'Email settings updated successfully!' });
    },
    onError: (error: { response?: { data?: { error?: string } } }) => {
      setTestStatus({ type: 'error', message: error.response?.data?.error || 'Failed to update settings' });
    }
  });

  const testEmailMutation = useMutation({
    mutationFn: async (email: string) => {
      const response = await processingApi.post('/api/admin/email/test', { email });
      return response.data;
    },
    onSuccess: () => {
      setTestStatus({ type: 'success', message: 'Test email sent successfully!' });
    },
    onError: (error: { response?: { data?: { error?: string } } }) => {
      setTestStatus({ type: 'error', message: error.response?.data?.error || 'Failed to send test email' });
    }
  });

  const handleTestEmail = (e: React.FormEvent) => {
    e.preventDefault();
    if (testEmail) {
      setTestStatus(null);
      testEmailMutation.mutate(testEmail);
    }
  };

  const handleSave = () => {
    const updateData: Partial<EmailConfig> & { smtp_password?: string; azure_client_secret?: string } = { ...formData };
    if (smtpPassword) {
      updateData.smtp_password = smtpPassword;
    }
    if (azureSecret) {
      updateData.azure_client_secret = azureSecret;
    }
    updateMutation.mutate(updateData);
  };

  const handleCancel = () => {
    setFormData(settings || {});
    setSmtpPassword('');
    setAzureSecret('');
    setIsEditing(false);
    setTestStatus(null);
  };

  if (isLoading) {
    return <div className="animate-pulse">Loading email settings...</div>;
  }

  if (error) {
    return <div className="text-red-500 dark:text-red-400">Error loading email settings. Please try refreshing the page.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Provider Selection */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Email Provider
          </h3>
          {!isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
            >
              Edit Settings
            </button>
          )}
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Email Provider
            </label>
            <select
              value={formData.email_provider || 'smtp'}
              onChange={(e) => setFormData({ ...formData, email_provider: e.target.value as 'smtp' | 'azure' })}
              disabled={!isEditing}
              className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400"
            >
              <option value="smtp">SMTP</option>
              <option value="azure">Azure Graph API</option>
            </select>
          </div>

          {!settings?.is_configured && (
            <div className="p-4 bg-yellow-50 dark:bg-yellow-900/50 rounded-md">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-yellow-700 dark:text-yellow-200">
                    Email is not fully configured. Please complete the configuration below.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* SMTP Configuration */}
      {formData.email_provider === 'smtp' && (
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            SMTP Configuration
          </h3>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                SMTP Server
              </label>
              <input
                type="text"
                value={formData.smtp_server || ''}
                onChange={(e) => setFormData({ ...formData, smtp_server: e.target.value })}
                disabled={!isEditing}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                SMTP Port
              </label>
              <input
                type="number"
                value={formData.smtp_port || ''}
                onChange={(e) => setFormData({ ...formData, smtp_port: parseInt(e.target.value) })}
                disabled={!isEditing}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Username
              </label>
              <input
                type="text"
                value={formData.smtp_username || ''}
                onChange={(e) => setFormData({ ...formData, smtp_username: e.target.value })}
                disabled={!isEditing}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Password {settings?.has_smtp_password && !isEditing && '(configured)'}
              </label>
              <input
                type="password"
                value={smtpPassword}
                onChange={(e) => setSmtpPassword(e.target.value)}
                disabled={!isEditing}
                placeholder={isEditing && settings?.has_smtp_password ? "Leave blank to keep current" : ""}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Encryption
              </label>
              <div className="mt-1 space-y-2">
                <label className="inline-flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.smtp_use_tls || false}
                    onChange={(e) => setFormData({ ...formData, smtp_use_tls: e.target.checked, smtp_use_ssl: false })}
                    disabled={!isEditing}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 disabled:opacity-50"
                  />
                  <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Use TLS</span>
                </label>
                <label className="inline-flex items-center ml-4">
                  <input
                    type="checkbox"
                    checked={formData.smtp_use_ssl || false}
                    onChange={(e) => setFormData({ ...formData, smtp_use_ssl: e.target.checked, smtp_use_tls: false })}
                    disabled={!isEditing}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 disabled:opacity-50"
                  />
                  <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Use SSL</span>
                </label>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Azure Configuration */}
      {formData.email_provider === 'azure' && (
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Azure Graph API Configuration
          </h3>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Tenant ID
              </label>
              <input
                type="text"
                value={formData.azure_tenant_id || ''}
                onChange={(e) => setFormData({ ...formData, azure_tenant_id: e.target.value })}
                disabled={!isEditing}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Client ID
              </label>
              <input
                type="text"
                value={formData.azure_client_id || ''}
                onChange={(e) => setFormData({ ...formData, azure_client_id: e.target.value })}
                disabled={!isEditing}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Client Secret {settings?.has_azure_secret && !isEditing && '(configured)'}
              </label>
              <input
                type="password"
                value={azureSecret}
                onChange={(e) => setAzureSecret(e.target.value)}
                disabled={!isEditing}
                placeholder={isEditing && settings?.has_azure_secret ? "Leave blank to keep current" : ""}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Sender Email (optional)
              </label>
              <input
                type="email"
                value={formData.azure_sender_email || ''}
                onChange={(e) => setFormData({ ...formData, azure_sender_email: e.target.value })}
                disabled={!isEditing}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400"
              />
            </div>

            <div className="col-span-2">
              <label className="inline-flex items-center">
                <input
                  type="checkbox"
                  checked={formData.azure_use_shared_mailbox || false}
                  onChange={(e) => setFormData({ ...formData, azure_use_shared_mailbox: e.target.checked })}
                  disabled={!isEditing}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 disabled:opacity-50"
                />
                <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Use shared mailbox</span>
              </label>
            </div>
          </div>

          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/50 rounded-md">
            <p className="text-sm text-blue-700 dark:text-blue-200">
              <strong>Required permissions:</strong> Mail.Send or Mail.Send.Shared (Application type)
            </p>
            <p className="text-sm text-blue-700 dark:text-blue-200 mt-1">
              Ensure admin consent is granted for the required permissions in Azure AD.
            </p>
          </div>
        </div>
      )}

      {/* General Email Settings */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          General Email Settings
        </h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              From Email
            </label>
            <input
              type="email"
              value={formData.from_email || ''}
              onChange={(e) => setFormData({ ...formData, from_email: e.target.value })}
              disabled={!isEditing}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              From Name
            </label>
            <input
              type="text"
              value={formData.from_name || ''}
              onChange={(e) => setFormData({ ...formData, from_name: e.target.value })}
              disabled={!isEditing}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Verification Subject
            </label>
            <input
              type="text"
              value={formData.verification_subject || ''}
              onChange={(e) => setFormData({ ...formData, verification_subject: e.target.value })}
              disabled={!isEditing}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Verification Expires (hours)
            </label>
            <input
              type="number"
              value={formData.verification_expires_hours || ''}
              onChange={(e) => setFormData({ ...formData, verification_expires_hours: parseInt(e.target.value) })}
              disabled={!isEditing}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400"
            />
          </div>
        </div>

        {isEditing && (
          <div className="mt-6 flex gap-3">
            <button
              onClick={handleSave}
              disabled={updateMutation.isPending}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </button>
            <button
              onClick={handleCancel}
              className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* Test Email Section */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Test Email Configuration
        </h3>
        
        <form onSubmit={handleTestEmail} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Send test email to:
            </label>
            <div className="mt-1 flex rounded-md shadow-sm">
              <input
                type="email"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                required
                className="flex-1 min-w-0 block w-full px-3 py-2 rounded-none rounded-l-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                placeholder="test@example.com"
              />
              <button
                type="submit"
                disabled={!settings?.is_configured || testEmailMutation.isPending}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-r-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {testEmailMutation.isPending ? 'Sending...' : 'Send Test'}
              </button>
            </div>
          </div>
          
          {testStatus && (
            <div className={`rounded-md p-4 ${
              testStatus.type === 'success' 
                ? 'bg-green-50 dark:bg-green-900/50' 
                : 'bg-red-50 dark:bg-red-900/50'
            }`}>
              <p className={`text-sm ${
                testStatus.type === 'success'
                  ? 'text-green-800 dark:text-green-200'
                  : 'text-red-800 dark:text-red-200'
              }`}>
                {testStatus.message}
              </p>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}