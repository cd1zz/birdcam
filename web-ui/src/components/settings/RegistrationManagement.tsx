import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { processingApi } from '../../api/client';

interface RegistrationLink {
  id: number;
  token: string;
  url: string;
  link_type: 'single_use' | 'multi_use';
  max_uses: number | null;
  uses: number;
  remaining_uses: number | null;
  expires_at: string | null;
  created_at: string;
  is_valid: boolean;
}

interface PendingRegistration {
  id: number;
  username: string;
  email: string;
  created_at: string;
  verification_expires: string | null;
}

export default function RegistrationManagement() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'links' | 'pending'>('links');
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  const [linkForm, setLinkForm] = useState({
    link_type: 'single_use' as 'single_use' | 'multi_use',
    max_uses: '',
    expires_hours: '24'
  });

  // Fetch registration links
  const { data: links = [], isLoading: linksLoading } = useQuery<RegistrationLink[]>({
    queryKey: ['registration-links'],
    queryFn: async () => {
      const response = await processingApi.get('/api/admin/registration/links');
      return response.data;
    }
  });

  // Fetch pending registrations
  const { data: pendingUsers = [], isLoading: pendingLoading } = useQuery<PendingRegistration[]>({
    queryKey: ['pending-registrations'],
    queryFn: async () => {
      const response = await processingApi.get('/api/admin/registration/pending');
      return response.data;
    }
  });

  // Generate registration link
  const generateLinkMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await processingApi.post('/api/admin/registration/generate-link', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['registration-links'] });
      setShowGenerateForm(false);
      setLinkForm({ link_type: 'single_use', max_uses: '', expires_hours: '24' });
    }
  });

  // Deactivate link
  const deactivateLinkMutation = useMutation({
    mutationFn: async (linkId: number) => {
      await processingApi.delete(`/api/admin/registration/links/${linkId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['registration-links'] });
    }
  });

  // Verify user manually
  const verifyUserMutation = useMutation({
    mutationFn: async (userId: number) => {
      await processingApi.post(`/api/admin/registration/verify/${userId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-registrations'] });
    }
  });

  const handleGenerateLink = (e: React.FormEvent) => {
    e.preventDefault();
    const data: any = {
      link_type: linkForm.link_type,
      expires_hours: linkForm.expires_hours ? parseInt(linkForm.expires_hours) : null
    };
    
    if (linkForm.link_type === 'multi_use' && linkForm.max_uses) {
      data.max_uses = parseInt(linkForm.max_uses);
    }
    
    generateLinkMutation.mutate(data);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // Could add a toast notification here
  };

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('links')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'links'
                ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
          >
            Registration Links
          </button>
          <button
            onClick={() => setActiveTab('pending')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'pending'
                ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
          >
            Pending Registrations
            {pendingUsers.length > 0 && (
              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                {pendingUsers.length}
              </span>
            )}
          </button>
        </nav>
      </div>

      {/* Registration Links Tab */}
      {activeTab === 'links' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Registration Links
            </h3>
            <button
              onClick={() => setShowGenerateForm(!showGenerateForm)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Generate New Link
            </button>
          </div>

          {/* Generate Link Form */}
          {showGenerateForm && (
            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
              <form onSubmit={handleGenerateLink} className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Link Type
                    </label>
                    <select
                      value={linkForm.link_type}
                      onChange={(e) => setLinkForm({ ...linkForm, link_type: e.target.value as any })}
                      className="mt-1 block w-full pl-3 pr-10 py-2 text-base text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                    >
                      <option value="single_use">Single Use</option>
                      <option value="multi_use">Multi Use</option>
                    </select>
                  </div>
                  
                  {linkForm.link_type === 'multi_use' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Max Uses (optional)
                      </label>
                      <input
                        type="number"
                        value={linkForm.max_uses}
                        onChange={(e) => setLinkForm({ ...linkForm, max_uses: e.target.value })}
                        className="mt-1 block w-full px-3 py-2 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 rounded-md"
                        placeholder="Unlimited"
                      />
                    </div>
                  )}
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Expires In (hours)
                    </label>
                    <input
                      type="number"
                      value={linkForm.expires_hours}
                      onChange={(e) => setLinkForm({ ...linkForm, expires_hours: e.target.value })}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-800 rounded-md"
                      placeholder="Never"
                    />
                  </div>
                </div>
                
                <div className="flex justify-end space-x-2">
                  <button
                    type="button"
                    onClick={() => setShowGenerateForm(false)}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={generateLinkMutation.isPending}
                    className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {generateLinkMutation.isPending ? 'Generating...' : 'Generate'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Links List */}
          {linksLoading ? (
            <div className="animate-pulse">Loading links...</div>
          ) : links.length === 0 ? (
            <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg">
              <p className="text-gray-500 dark:text-gray-400">No registration links created yet</p>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
              <ul className="divide-y divide-gray-200 dark:divide-gray-700">
                {links.map((link) => (
                  <li key={link.id} className="px-6 py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            link.is_valid 
                              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                              : 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
                          }`}>
                            {link.is_valid ? 'Active' : 'Inactive'}
                          </span>
                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                            {link.link_type === 'single_use' ? 'Single Use' : 'Multi Use'}
                          </span>
                          {link.uses > 0 && (
                            <span className="text-sm text-gray-500 dark:text-gray-400">
                              Used {link.uses} {link.uses === 1 ? 'time' : 'times'}
                            </span>
                          )}
                        </div>
                        <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                          {link.expires_at 
                            ? `Expires ${new Date(link.expires_at).toLocaleString()}`
                            : 'No expiration'}
                          {link.remaining_uses !== null && ` • ${link.remaining_uses} uses remaining`}
                        </div>
                        <div className="mt-2 flex items-center space-x-2">
                          <code className="text-xs text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-900 px-2 py-1 rounded">
                            {link.url}
                          </code>
                          <button
                            onClick={() => copyToClipboard(link.url)}
                            className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
                          >
                            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                          </button>
                        </div>
                      </div>
                      {link.is_valid && (
                        <button
                          onClick={() => deactivateLinkMutation.mutate(link.id)}
                          className="ml-4 text-red-600 hover:text-red-500 dark:text-red-400"
                        >
                          Deactivate
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Pending Registrations Tab */}
      {activeTab === 'pending' && (
        <div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Pending Email Verifications
          </h3>
          
          {pendingLoading ? (
            <div className="animate-pulse">Loading pending registrations...</div>
          ) : pendingUsers.length === 0 ? (
            <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg">
              <p className="text-gray-500 dark:text-gray-400">No pending registrations</p>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
              <ul className="divide-y divide-gray-200 dark:divide-gray-700">
                {pendingUsers.map((user) => (
                  <li key={user.id} className="px-6 py-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {user.username}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {user.email}
                        </p>
                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                          Registered {new Date(user.created_at).toLocaleString()}
                          {user.verification_expires && 
                            ` • Expires ${new Date(user.verification_expires).toLocaleString()}`}
                        </p>
                      </div>
                      <button
                        onClick={() => verifyUserMutation.mutate(user.id)}
                        className="ml-4 inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-indigo-700 bg-indigo-100 hover:bg-indigo-200 dark:bg-indigo-900 dark:text-indigo-200 dark:hover:bg-indigo-800"
                      >
                        Verify Manually
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}