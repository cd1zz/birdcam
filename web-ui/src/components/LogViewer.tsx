import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';

interface LogEntry {
  timestamp: string;
  level: string;
  service: string;
  unit?: string;
  message: string;
  syslog_identifier?: string;
  hostname?: string;
  source?: 'local' | 'remote';
}

interface LogViewerProps {
  service?: 'pi-capture' | 'ai-processor' | 'combined' | 'pi-capture-remote' | 'security';
}

const LogViewer: React.FC<LogViewerProps> = ({ service = 'combined' }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lines, setLines] = useState(100);
  const [since, setSince] = useState('1h');
  const [levels, setLevels] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [selectedService, setSelectedService] = useState(service);
  
  const intervalRef = useRef<number | null>(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = {
        lines,
        since,
        ...(levels.length > 0 && { levels: levels.join(',') }),
        ...(search && { search }),
        ...(selectedService !== 'combined' && { service: selectedService })
      };

      let response;
      if (selectedService === 'combined') {
        response = await api.logs.getCombinedLogs(params);
      } else if (selectedService === 'pi-capture') {
        response = await api.logs.getPiCaptureLogs(params);
      } else if (selectedService === 'pi-capture-remote') {
        response = await api.logs.getRemotePiCaptureLogs(params);
      } else if (selectedService === 'security') {
        // Fetch and transform security logs to match LogEntry format
        const securityResponse = await api.security.getLogs({ 
          hours: since === '1h' ? 1 : since === '6h' ? 6 : since === '24h' ? 24 : 168
        });
        const securityLogs = securityResponse.logs.map((log: any) => ({
          timestamp: log.timestamp,
          level: log.severity || 'INFO',
          service: 'security',
          message: `[${log.event_type}] ${log.username || 'N/A'} - ${log.failure_reason || log.event_type}`,
          syslog_identifier: 'birdcam.security.audit',
          hostname: log.ip_address || 'N/A',
          source: 'local' as const
        }));
        response = { logs: securityLogs };
      } else {
        response = await api.logs.getAiProcessorLogs(params);
      }
      
      setLogs(response.logs);
    } catch (err) {
      const error = err as { response?: { data?: { error?: string } } };
      setError(error.response?.data?.error || 'Failed to fetch logs');
    } finally {
      setLoading(false);
    }
  }, [lines, since, levels, search, selectedService]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = window.setInterval(fetchLogs, 5000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, fetchLogs]);

  const handleExport = async () => {
    try {
      const params = {
        since,
        format: 'text',
        ...(levels.length > 0 && { levels: levels.join(',') }),
        ...(selectedService !== 'combined' && { service: selectedService })
      };
      
      const blob = await api.logs.exportLogs(params);
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      link.setAttribute('download', `birdcam_logs_${timestamp}.txt`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      setError('Failed to export logs');
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return 'text-red-600 bg-red-100 dark:bg-red-900/20';
      case 'WARNING': return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/20';
      case 'INFO': return 'text-blue-600 bg-blue-100 dark:bg-blue-900/20';
      case 'DEBUG': return 'text-gray-600 bg-gray-100 dark:bg-gray-900/20';
      case 'ACCESS': return 'text-green-600 bg-green-100 dark:bg-green-900/20';
      default: return 'text-gray-600 bg-gray-100 dark:bg-gray-900/20';
    }
  };

  const getServiceColor = (service: string, source?: string) => {
    switch (service) {
      case 'pi-capture': 
        return source === 'remote' ? 'bg-green-500 text-white' : 'bg-green-600 text-white';
      case 'ai-processor': return 'bg-blue-600 text-white';
      case 'access': return 'bg-orange-600 text-white';
      case 'security': return 'bg-red-600 text-white';
      default: return 'bg-gray-600 text-white';
    }
  };

  const getMessageStyle = (log: LogEntry) => {
    // Highlight security events
    if (log.service === 'security' && log.message.includes('[auth_failed]')) {
      return 'text-red-600 dark:text-red-400 font-semibold';
    } else if (log.service === 'security' && log.message.includes('[auth_success]')) {
      return 'text-green-600 dark:text-green-400';
    } else if (log.service === 'security') {
      return 'text-blue-600 dark:text-blue-400';
    }
    return 'text-gray-900 dark:text-gray-100';
  };

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">System Logs</h3>
          <div className="flex gap-2">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                autoRefresh
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              {autoRefresh ? 'Auto Refresh On' : 'Auto Refresh Off'}
            </button>
            <button
              onClick={fetchLogs}
              disabled={loading || autoRefresh}
              className="px-4 py-2 text-sm font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              Refresh
            </button>
            <button
              onClick={handleExport}
              className="px-4 py-2 text-sm font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
            >
              Export
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Service</label>
            <select
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value as 'pi-capture' | 'ai-processor' | 'combined' | 'pi-capture-remote' | 'security')}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="combined">All Services</option>
              <option value="pi-capture">Pi Capture (Local)</option>
              <option value="pi-capture-remote">Pi Capture (Remote)</option>
              <option value="ai-processor">AI Processor</option>
              <option value="security">Security Audit</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Lines</label>
            <select
              value={lines}
              onChange={(e) => setLines(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
              <option value={500}>500</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Since</label>
            <select
              value={since}
              onChange={(e) => setSince(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="5m">5 minutes</option>
              <option value="15m">15 minutes</option>
              <option value="30m">30 minutes</option>
              <option value="1h">1 hour</option>
              <option value="6h">6 hours</option>
              <option value="12h">12 hours</option>
              <option value="24h">24 hours</option>
              <option value="2d">2 days</option>
              <option value="7d">7 days</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Level</label>
            <div className="relative">
              <div className="flex flex-wrap gap-2 p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700">
                {['ERROR', 'WARNING', 'INFO', 'DEBUG', 'ACCESS'].map((levelOption) => (
                  <label
                    key={levelOption}
                    className="flex items-center gap-1 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={levels.includes(levelOption)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setLevels([...levels, levelOption]);
                        } else {
                          setLevels(levels.filter(l => l !== levelOption));
                        }
                      }}
                      className="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
                    />
                    <span className={`text-sm ${
                      levelOption === 'ERROR' ? 'text-red-600 dark:text-red-400' :
                      levelOption === 'WARNING' ? 'text-yellow-600 dark:text-yellow-400' :
                      levelOption === 'ACCESS' ? 'text-green-600 dark:text-green-400' :
                      'text-gray-700 dark:text-gray-300'
                    }`}>
                      {levelOption}
                    </span>
                  </label>
                ))}
                {levels.length > 0 && (
                  <button
                    onClick={() => setLevels([])}
                    className="ml-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Search</label>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && fetchLogs()}
              placeholder="Search logs..."
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Log entries */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm">
        <div className="p-4 max-h-[600px] overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : logs.length === 0 ? (
            <p className="text-center text-gray-500 dark:text-gray-400 py-8">No logs found</p>
          ) : (
            <div className="space-y-1">
              {logs.map((log, index) => (
                <div
                  key={index}
                  className="p-3 border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 font-mono text-sm"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-gray-600 dark:text-gray-400">
                      {log.timestamp}
                    </span>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded ${getLevelColor(log.level)}`}>
                      {log.level}
                    </span>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded ${getServiceColor(log.service, log.source)}`}>
                      {log.service}
                    </span>
                    {log.hostname && (
                      <span className="px-2 py-0.5 text-xs font-medium rounded bg-purple-600 text-white">
                        {log.hostname}
                      </span>
                    )}
                    {log.unit && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {log.unit}
                      </span>
                    )}
                  </div>
                  <div className={`whitespace-pre-wrap break-words ${getMessageStyle(log)}`}>
                    {log.message}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LogViewer;