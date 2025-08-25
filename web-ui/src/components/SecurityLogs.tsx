import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { AlertTriangle, Shield, UserX, Clock, Filter, RefreshCw } from 'lucide-react';

interface SecurityLog {
  timestamp: string;
  event_type: string;
  username?: string;
  ip_address?: string;
  user_agent?: string;
  failure_reason?: string;
  request_id?: string;
  request_path?: string;
  severity?: string;
  target_username?: string;
  new_role?: string;
  changed_by?: string;
  deactivated_by?: string;
}

interface SecuritySummary {
  total_events: number;
  failed_logins: number;
  successful_logins: number;
  password_changes: number;
  role_changes: number;
  user_deactivations: number;
  failed_by_reason: Record<string, number>;
  failed_by_username: Record<string, number>;
  failed_by_ip: Record<string, number>;
  events_by_hour: Record<string, number>;
}

export default function SecurityLogs() {
  const [hours, setHours] = useState(24);
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('');
  const [usernameFilter, setUsernameFilter] = useState('');
  const [ipFilter, setIpFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Fetch security logs
  const { data: logsData, isLoading: logsLoading, refetch: refetchLogs } = useQuery({
    queryKey: ['securityLogs', hours, eventTypeFilter, usernameFilter, ipFilter],
    queryFn: () => api.security.getLogs({
      hours,
      event_type: eventTypeFilter || undefined,
      username: usernameFilter || undefined,
      ip_address: ipFilter || undefined,
    }),
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  });

  // Fetch security summary
  const { data: summaryData, isLoading: summaryLoading } = useQuery({
    queryKey: ['securitySummary', hours],
    queryFn: () => api.security.getSummary({ hours }),
    refetchInterval: 30000,
  });

  const logs: SecurityLog[] = logsData?.logs || [];
  const summary: SecuritySummary = summaryData || {
    total_events: 0,
    failed_logins: 0,
    successful_logins: 0,
    password_changes: 0,
    role_changes: 0,
    user_deactivations: 0,
    failed_by_reason: {},
    failed_by_username: {},
    failed_by_ip: {},
    events_by_hour: {},
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'auth_failed':
        return <UserX className="h-4 w-4 text-red-500" />;
      case 'auth_success':
        return <Shield className="h-4 w-4 text-green-500" />;
      case 'password_changed':
      case 'role_changed':
      case 'user_deactivated':
        return <Shield className="h-4 w-4 text-blue-500" />;
      default:
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getEventDescription = (log: SecurityLog) => {
    switch (log.event_type) {
      case 'auth_failed':
        return `Failed login attempt: ${log.failure_reason?.replace('_', ' ')}`;
      case 'auth_success':
        return 'Successful login';
      case 'password_changed':
        return 'Password changed';
      case 'role_changed':
        return `Role changed to ${log.new_role} by ${log.changed_by}`;
      case 'user_deactivated':
        return `User deactivated by ${log.deactivated_by}`;
      case 'token_refresh_failed':
        return `Token refresh failed: ${log.failure_reason}`;
      default:
        return log.event_type;
    }
  };

  const getFailureReasonBadge = (reason: string) => {
    const colors: Record<string, string> = {
      user_not_found: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      invalid_password: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      account_disabled: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
    };
    return colors[reason] || 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
  };

  return (
    <div className="space-y-6">
      {/* Summary Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Failed Logins</h3>
            <UserX className="h-5 w-5 text-red-500" />
          </div>
          <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
            {summary.failed_logins}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Last {hours} hours</p>
        </div>

        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Successful Logins</h3>
            <Shield className="h-5 w-5 text-green-500" />
          </div>
          <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
            {summary.successful_logins}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Last {hours} hours</p>
        </div>

        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Top Failed IP</h3>
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
          </div>
          <p className="mt-2 text-lg font-semibold text-gray-900 dark:text-white truncate">
            {Object.entries(summary.failed_by_ip)[0]?.[0] || 'None'}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {Object.entries(summary.failed_by_ip)[0]?.[1] || 0} attempts
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Security Events</h3>
            <Clock className="h-5 w-5 text-blue-500" />
          </div>
          <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
            {summary.total_events}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Last {hours} hours</p>
        </div>
      </div>

      {/* Failed Login Reasons */}
      {Object.keys(summary.failed_by_reason).length > 0 && (
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-3">
            Failed Login Reasons
          </h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(summary.failed_by_reason).map(([reason, count]) => (
              <span
                key={reason}
                className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getFailureReasonBadge(reason)}`}
              >
                {reason.replace('_', ' ')}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Time Range:
            </label>
            <select
              value={hours}
              onChange={(e) => setHours(Number(e.target.value))}
              className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value={1}>Last 1 hour</option>
              <option value={6}>Last 6 hours</option>
              <option value={24}>Last 24 hours</option>
              <option value={48}>Last 48 hours</option>
              <option value={168}>Last 7 days</option>
            </select>
          </div>

          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md text-gray-700 dark:text-gray-300"
          >
            <Filter className="h-4 w-4" />
            Filters
          </button>

          <button
            onClick={() => refetchLogs()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded-md text-white"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Event Type
              </label>
              <select
                value={eventTypeFilter}
                onChange={(e) => setEventTypeFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="">All Events</option>
                <option value="auth_failed">Failed Logins</option>
                <option value="auth_success">Successful Logins</option>
                <option value="password_changed">Password Changes</option>
                <option value="role_changed">Role Changes</option>
                <option value="user_deactivated">User Deactivations</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Username
              </label>
              <input
                type="text"
                value={usernameFilter}
                onChange={(e) => setUsernameFilter(e.target.value)}
                placeholder="Filter by username"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                IP Address
              </label>
              <input
                type="text"
                value={ipFilter}
                onChange={(e) => setIpFilter(e.target.value)}
                placeholder="Filter by IP"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          </div>
        )}
      </div>

      {/* Security Logs Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Security Event Log
          </h3>
        </div>

        {logsLoading || summaryLoading ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            Loading security logs...
          </div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            No security events found for the selected time range
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Event
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Username
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    IP Address
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Details
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {logs.map((log, index) => (
                  <tr key={`${log.request_id}-${index}`} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {formatTimestamp(log.timestamp)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {getEventIcon(log.event_type)}
                        <span className="text-sm text-gray-900 dark:text-white">
                          {getEventDescription(log)}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {log.username || log.target_username || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {log.ip_address || '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      <div className="max-w-xs truncate" title={log.user_agent}>
                        {log.user_agent ? log.user_agent.substring(0, 50) + '...' : '-'}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}