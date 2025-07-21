import React, { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import DetectionGrid from '../components/DetectionGrid';
import { api, type Detection } from '../api/client';

const Detections: React.FC = () => {
  const [selectedSpecies, setSelectedSpecies] = useState<string>('all');
  const [dateRange, setDateRange] = useState<'today' | 'week' | 'month' | 'all'>('week');
  const [selectedVideo, setSelectedVideo] = useState<Detection | null>(null);

  const getDateRange = useCallback(() => {
    const end = new Date();
    const start = new Date();
    
    switch (dateRange) {
      case 'today':
        start.setHours(0, 0, 0, 0);
        break;
      case 'week':
        start.setDate(start.getDate() - 7);
        break;
      case 'month':
        start.setMonth(start.getMonth() - 1);
        break;
      default:
        return {};
    }
    
    // Format dates to match database format (local time without timezone)
    const formatToLocal = (date: Date) => {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      const ms = String(date.getMilliseconds()).padStart(3, '0');
      return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}.${ms}`;
    };
    
    return {
      start: formatToLocal(start),
      end: formatToLocal(end),
    };
  }, [dateRange]);

  const { 
    data: detections, 
    isLoading, 
    error,
    isError,
    refetch
  } = useQuery({
    queryKey: ['detections', selectedSpecies, dateRange],
    queryFn: async () => {
      const params = {
        ...getDateRange(),
        species: selectedSpecies === 'all' ? undefined : selectedSpecies,
        limit: 50,
        sort: 'desc' as const,
      };
      return api.detections.getRecent(params);
    },
    refetchInterval: 60000,
    retry: (failureCount, error: unknown) => {
      // Don't retry on 4xx errors (client errors)
      const apiError = error as { response?: { status?: number } };
      if (apiError?.response?.status && apiError.response.status >= 400 && apiError.response.status < 500) {
        return false;
      }
      return failureCount < 3;
    },
  });

  // Get unique species from detections for filter
  const species = useMemo(() => {
    if (!detections) return [];
    const uniqueSpecies = new Set(detections.map(d => d.species));
    return Array.from(uniqueSpecies).sort();
  }, [detections]);

  const handleVideoClick = useCallback((detection: Detection) => {
    setSelectedVideo(detection);
  }, []);

  const handleRetry = useCallback(() => {
    refetch();
  }, [refetch]);

  const closeVideoModal = useCallback(() => {
    setSelectedVideo(null);
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-300">Loading detections...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    const errorMessage = (error as Error)?.message || 'Failed to load detections. Please try again.';
    
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <span className="text-red-500 text-xl">⚠️</span>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Loading Error</h3>
              <p className="text-red-700 dark:text-red-300 mt-1">{errorMessage}</p>
            </div>
          </div>
          <button
            onClick={handleRetry}
            className="ml-4 px-4 py-2 bg-red-600 dark:bg-red-700 text-white rounded hover:bg-red-700 dark:hover:bg-red-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4 mb-6">
        <div className="flex flex-col sm:flex-row flex-wrap items-start sm:items-center gap-4">
          {/* Species Filter */}
          <div className="w-full sm:w-auto">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Species</label>
            <select
              value={selectedSpecies}
              onChange={(e) => setSelectedSpecies(e.target.value)}
              className="block w-full sm:w-40 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Species</option>
              {species.map((s) => (
                <option key={s} value={s}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Date Range Filter */}
          <div className="w-full sm:w-auto">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Time Period</label>
            <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1 overflow-x-auto">
              {(['today', 'week', 'month', 'all'] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setDateRange(range)}
                  className={`px-2 sm:px-3 py-1 text-sm sm:text-base rounded capitalize transition-colors whitespace-nowrap ${
                    dateRange === range
                      ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
                  }`}
                >
                  {range === 'week' ? 'This Week' : range === 'all' ? 'All Time' : range}
                </button>
              ))}
            </div>
          </div>

          {/* Stats */}
          {detections && (
            <div className="w-full sm:ml-auto sm:w-auto text-center sm:text-right">
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Detections</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{detections.length}</p>
            </div>
          )}
        </div>
      </div>

      {/* Detection Grid */}
      <DetectionGrid 
        detections={detections || []} 
        onVideoClick={handleVideoClick}
      />

      {/* Video Modal */}
      {selectedVideo && (
        <div 
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-2 sm:p-4"
          onClick={closeVideoModal}
        >
          <div 
            className="bg-white dark:bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-3 sm:p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 flex-1 min-w-0">
                <span className="text-2xl">
                  {selectedVideo.species === 'bird' ? '🦅' : 
                   selectedVideo.species === 'cat' ? '🐱' : 
                   selectedVideo.species === 'dog' ? '🐕' : '🐾'}
                </span>
                {selectedVideo.species.charAt(0).toUpperCase() + selectedVideo.species.slice(1)} Detection
                {selectedVideo.count && selectedVideo.count > 1 && (
                  <span className="text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded">
                    {selectedVideo.count} detections
                  </span>
                )}
              </h3>
              <button
                onClick={closeVideoModal}
                className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 text-xl sm:text-2xl leading-none p-1 ml-2 flex-shrink-0"
                aria-label="Close video"
              >
                ✕
              </button>
            </div>
            <div className="p-3 sm:p-4">
              <video
                controls
                autoPlay
                className="w-full rounded"
                src={api.detections.getVideo(selectedVideo.filename || selectedVideo.video_path?.split('/').pop() || '')}
                onError={(e) => {
                  console.error('Video failed to load:', e);
                }}
              />
              <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs sm:text-sm text-gray-600 dark:text-gray-300">
                <div>
                  <p><strong>Confidence:</strong> {(selectedVideo.confidence * 100).toFixed(1)}%</p>
                  <p><strong>Time:</strong> {new Date(selectedVideo.received_time || selectedVideo.timestamp || '').toLocaleString()}</p>
                </div>
                <div>
                  <p><strong>File:</strong> {selectedVideo.filename || selectedVideo.video_path?.split('/').pop() || 'No file'}</p>
                  {selectedVideo.duration && (
                    <p><strong>Duration:</strong> {selectedVideo.duration}s</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Detections;