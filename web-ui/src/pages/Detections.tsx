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
    
    return {
      start: start.toISOString(),
      end: end.toISOString(),
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
    retry: (failureCount, error: any) => {
      // Don't retry on 4xx errors (client errors)
      if (error?.response?.status >= 400 && error?.response?.status < 500) {
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
          <p className="mt-4 text-gray-600">Loading detections...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    const errorMessage = (error as any)?.userMessage || 'Failed to load detections. Please try again.';
    
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <span className="text-red-500 text-xl">⚠️</span>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Loading Error</h3>
              <p className="text-red-700 mt-1">{errorMessage}</p>
            </div>
          </div>
          <button
            onClick={handleRetry}
            className="ml-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
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
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          {/* Species Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Species</label>
            <select
              value={selectedSpecies}
              onChange={(e) => setSelectedSpecies(e.target.value)}
              className="block w-40 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
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
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Time Period</label>
            <div className="flex bg-gray-100 rounded-lg p-1">
              {(['today', 'week', 'month', 'all'] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setDateRange(range)}
                  className={`px-3 py-1 rounded capitalize transition-colors ${
                    dateRange === range
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {range === 'week' ? 'This Week' : range === 'all' ? 'All Time' : range}
                </button>
              ))}
            </div>
          </div>

          {/* Stats */}
          {detections && (
            <div className="ml-auto text-right">
              <p className="text-sm text-gray-500">Total Detections</p>
              <p className="text-2xl font-semibold text-gray-900">{detections.length}</p>
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
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={closeVideoModal}
        >
          <div 
            className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="text-lg font-semibold flex items-center gap-2">
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
                className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
                aria-label="Close video"
              >
                ✕
              </button>
            </div>
            <div className="p-4">
              <video
                controls
                autoPlay
                className="w-full rounded"
                src={api.detections.getVideo(selectedVideo.filename || selectedVideo.video_path?.split('/').pop() || '')}
                onError={(e) => {
                  console.error('Video failed to load:', e);
                }}
              />
              <div className="mt-4 grid grid-cols-2 gap-4 text-sm text-gray-600">
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