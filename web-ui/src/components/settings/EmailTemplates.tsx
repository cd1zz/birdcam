import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';

interface EmailTemplateFormData {
  subject: string;
  body_text: string;
  body_html: string;
  is_active: boolean;
}

const TEMPLATE_NAMES: Record<string, string> = {
  verification: 'Email Verification',
  welcome: 'Welcome Email',
  password_reset: 'Password Reset',
  registration_invite: 'Registration Invitation'
};

const EmailTemplates: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedTemplate, setSelectedTemplate] = useState<string>('registration_invite');
  const [editMode, setEditMode] = useState<boolean>(false);
  const [showPreview, setShowPreview] = useState<boolean>(false);
  const [previewFormat, setPreviewFormat] = useState<'text' | 'html'>('html');
  const [formData, setFormData] = useState<EmailTemplateFormData>({
    subject: '',
    body_text: '',
    body_html: '',
    is_active: true
  });
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteMessage, setInviteMessage] = useState('');
  const [sendingInvite, setSendingInvite] = useState(false);

  // Fetch templates
  const { isLoading } = useQuery({
    queryKey: ['emailTemplates'],
    queryFn: async () => {
      const response = await api.admin.getEmailTemplates();
      return response.templates;
    }
  });

  // Fetch specific template
  const { data: currentTemplate } = useQuery({
    queryKey: ['emailTemplate', selectedTemplate],
    queryFn: async () => {
      const response = await api.admin.getEmailTemplate(selectedTemplate);
      return response;
    },
    enabled: !!selectedTemplate
  });

  // Update template mutation
  const updateMutation = useMutation({
    mutationFn: async (data: EmailTemplateFormData) => {
      return api.admin.updateEmailTemplate(selectedTemplate, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emailTemplates'] });
      queryClient.invalidateQueries({ queryKey: ['emailTemplate', selectedTemplate] });
      setEditMode(false);
    }
  });

  // Reset template mutation
  const resetMutation = useMutation({
    mutationFn: async () => {
      return api.admin.resetEmailTemplate(selectedTemplate);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emailTemplates'] });
      queryClient.invalidateQueries({ queryKey: ['emailTemplate', selectedTemplate] });
      setEditMode(false);
    }
  });

  // Preview template
  const { data: preview, refetch: fetchPreview } = useQuery({
    queryKey: ['emailTemplatePreview', selectedTemplate, previewFormat],
    queryFn: async () => {
      const response = await api.admin.previewEmailTemplate(selectedTemplate, {
        format: previewFormat
      });
      return response.preview;
    },
    enabled: false
  });

  // Send invite mutation
  const sendInviteMutation = useMutation({
    mutationFn: async (data: { email: string; message?: string }) => {
      return api.admin.sendRegistrationInvite(data);
    },
    onSuccess: () => {
      setInviteEmail('');
      setInviteMessage('');
      setSendingInvite(false);
    },
    onError: () => {
      setSendingInvite(false);
    }
  });

  React.useEffect(() => {
    if (currentTemplate) {
      setFormData({
        subject: currentTemplate.subject,
        body_text: currentTemplate.body_text,
        body_html: currentTemplate.body_html,
        is_active: currentTemplate.is_active
      });
    }
  }, [currentTemplate]);

  const handleSave = () => {
    updateMutation.mutate(formData);
  };

  const handleReset = () => {
    if (window.confirm('Are you sure you want to reset this template to its default values?')) {
      resetMutation.mutate();
    }
  };

  const handlePreview = () => {
    setShowPreview(true);
    fetchPreview();
  };

  const handleSendInvite = () => {
    setSendingInvite(true);
    sendInviteMutation.mutate({
      email: inviteEmail,
      message: inviteMessage || undefined
    });
  };

  const getVariables = () => {
    if (!currentTemplate) return [];
    try {
      const vars = JSON.parse(currentTemplate.variables || '{}');
      return Object.entries(vars).map(([key, desc]) => ({ key, description: desc as string }));
    } catch {
      return [];
    }
  };

  if (isLoading) {
    return <div className="text-center py-8">Loading templates...</div>;
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
      <h3 className="text-lg font-semibold mb-6 text-gray-900 dark:text-white">Email Templates</h3>

      {/* Template Selector */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Select Template
        </label>
        <select
          value={selectedTemplate}
          onChange={(e) => {
            setSelectedTemplate(e.target.value);
            setEditMode(false);
          }}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        >
          {Object.entries(TEMPLATE_NAMES).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      {/* Send Invitation Section (only for registration_invite) */}
      {selectedTemplate === 'registration_invite' && (
        <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <h4 className="font-medium text-blue-900 dark:text-blue-200 mb-4">Send Registration Invitation</h4>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="user@example.com"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Personal Message (Optional)
              </label>
              <textarea
                value={inviteMessage}
                onChange={(e) => setInviteMessage(e.target.value)}
                placeholder="Welcome to our bird monitoring community..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <button
              onClick={handleSendInvite}
              disabled={!inviteEmail || sendingInvite || sendInviteMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sendingInvite ? 'Sending...' : 'Send Invitation'}
            </button>
            {sendInviteMutation.isSuccess && (
              <p className="text-sm text-green-600 dark:text-green-400">
                Invitation sent successfully!
              </p>
            )}
            {sendInviteMutation.isError && (
              <p className="text-sm text-red-600 dark:text-red-400">
                Failed to send invitation. Please try again.
              </p>
            )}
          </div>
        </div>
      )}

      {currentTemplate && (
        <>
          {/* Template Info */}
          <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700 rounded">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                  {TEMPLATE_NAMES[selectedTemplate] || selectedTemplate}
                </h4>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Status: <span className={currentTemplate.is_active ? 'text-green-600' : 'text-red-600'}>
                    {currentTemplate.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handlePreview}
                  className="px-3 py-1 text-sm bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded hover:bg-gray-300 dark:hover:bg-gray-500"
                >
                  Preview
                </button>
                {!editMode ? (
                  <button
                    onClick={() => setEditMode(true)}
                    className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Edit
                  </button>
                ) : (
                  <>
                    <button
                      onClick={handleSave}
                      disabled={updateMutation.isPending}
                      className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditMode(false)}
                      className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleReset}
                      disabled={resetMutation.isPending}
                      className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                    >
                      Reset
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Available Variables */}
          <div className="mb-6">
            <h5 className="font-medium text-gray-900 dark:text-white mb-2">Available Variables</h5>
            <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
              {getVariables().map(({ key, description }) => (
                <div key={key}>
                  <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">{`{{${key}}}`}</code>
                  <span className="ml-2">{description}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Template Editor */}
          {editMode && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Subject
                </label>
                <input
                  type="text"
                  value={formData.subject}
                  onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Plain Text Version
                </label>
                <textarea
                  value={formData.body_text}
                  onChange={(e) => setFormData({ ...formData, body_text: e.target.value })}
                  rows={10}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  HTML Version
                </label>
                <textarea
                  value={formData.body_html}
                  onChange={(e) => setFormData({ ...formData, body_html: e.target.value })}
                  rows={15}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="mr-2"
                  />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Template is active
                  </span>
                </label>
              </div>
            </div>
          )}

          {/* Preview Modal */}
          {showPreview && preview && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full max-h-[80vh] overflow-hidden m-4">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      Template Preview
                    </h3>
                    <button
                      onClick={() => setShowPreview(false)}
                      className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => setPreviewFormat('html')}
                      className={`px-3 py-1 text-sm rounded ${
                        previewFormat === 'html'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200'
                      }`}
                    >
                      HTML
                    </button>
                    <button
                      onClick={() => setPreviewFormat('text')}
                      className={`px-3 py-1 text-sm rounded ${
                        previewFormat === 'text'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200'
                      }`}
                    >
                      Plain Text
                    </button>
                  </div>
                </div>
                <div className="p-4 overflow-auto max-h-[60vh]">
                  {previewFormat === 'html' ? (
                    <div dangerouslySetInnerHTML={{ __html: preview }} />
                  ) : (
                    <pre className="whitespace-pre-wrap font-mono text-sm">{preview}</pre>
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Success/Error Messages */}
      {updateMutation.isSuccess && (
        <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300 rounded">
          Template updated successfully!
        </div>
      )}
      {resetMutation.isSuccess && (
        <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300 rounded">
          Template reset to default values!
        </div>
      )}
    </div>
  );
};

export default EmailTemplates;