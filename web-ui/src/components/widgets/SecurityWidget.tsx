import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/client';
import { Shield, UserX, AlertTriangle } from 'lucide-react';
import { Link } from 'react-router-dom';

export function RecentFailedLoginsWidget() {
  const { data, isLoading } = useQuery({
    queryKey: ['securitySummary', 1],
    queryFn: () => api.security.getSummary({ hours: 1 }),
    refetchInterval: 60000, // Refresh every minute
  });

  const failedLogins = data?.failed_logins || 0;
  const topFailedIp = Object.entries(data?.failed_by_ip || {})[0] as [string, number] | undefined;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Security Status</h3>
        <UserX className="h-5 w-5 text-red-500" />
      </div>
      
      {isLoading ? (
        <div className="animate-pulse space-y-2">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
        </div>
      ) : (
        <>
          <div className="mb-4">
            <div className="flex items-baseline">
              <span className="text-3xl font-bold text-gray-900 dark:text-white">
                {failedLogins}
              </span>
              <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">
                failed login{failedLogins !== 1 ? 's' : ''} (last hour)
              </span>
            </div>
            
            {topFailedIp && (
              <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Most attempts from: <span className="font-mono">{topFailedIp[0]}</span> ({topFailedIp[1]} attempts)
              </div>
            )}
          </div>
          
          <Link
            to="/admin"
            state={{ tab: 'security' } as any}
            className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
          >
            View security logs →
          </Link>
        </>
      )}
    </div>
  );
}

export function AccountLockoutWidget() {
  const { data, isLoading } = useQuery({
    queryKey: ['lockedUsers'],
    queryFn: api.security.getLockedUsers,
    refetchInterval: 60000, // Refresh every minute
  });

  const lockedUsers = data?.users?.filter((u: any) => u.is_locked) || [];
  const suspiciousUsers = data?.users?.filter((u: any) => u.recent_attempts >= 3 && !u.is_locked) || [];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Account Status</h3>
        <Shield className="h-5 w-5 text-blue-500" />
      </div>
      
      {isLoading ? (
        <div className="animate-pulse space-y-2">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
        </div>
      ) : (
        <>
          {lockedUsers.length > 0 ? (
            <div className="mb-4">
              <div className="flex items-center gap-2 text-red-600 dark:text-red-400 mb-2">
                <AlertTriangle className="h-4 w-4" />
                <span className="font-semibold">{lockedUsers.length} account{lockedUsers.length !== 1 ? 's' : ''} locked</span>
              </div>
              <div className="space-y-1">
                {lockedUsers.slice(0, 3).map((user: any) => (
                  <div key={user.username} className="text-sm text-gray-600 dark:text-gray-400">
                    <span className="font-mono">{user.username}</span> - {user.recent_attempts} attempts
                  </div>
                ))}
                {lockedUsers.length > 3 && (
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    and {lockedUsers.length - 3} more...
                  </div>
                )}
              </div>
            </div>
          ) : suspiciousUsers.length > 0 ? (
            <div className="mb-4">
              <div className="flex items-center gap-2 text-yellow-600 dark:text-yellow-400 mb-2">
                <AlertTriangle className="h-4 w-4" />
                <span className="font-semibold">Suspicious activity</span>
              </div>
              <div className="space-y-1">
                {suspiciousUsers.slice(0, 3).map((user: any) => (
                  <div key={user.username} className="text-sm text-gray-600 dark:text-gray-400">
                    <span className="font-mono">{user.username}</span> - {user.recent_attempts} recent attempts
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-green-600 dark:text-green-400">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4" />
                <span>All accounts secure</span>
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                No suspicious login activity detected
              </p>
            </div>
          )}
          
          <Link
            to="/admin"
            state={{ tab: 'security' } as any}
            className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
          >
            View all activity →
          </Link>
        </>
      )}
    </div>
  );
}