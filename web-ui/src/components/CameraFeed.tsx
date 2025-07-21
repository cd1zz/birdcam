import React, { useState, useRef, useEffect } from 'react';
import { api } from '../api/client';

interface CameraFeedProps {
  cameraId: number;
  cameraName: string;
  className?: string;
}

const CameraFeed: React.FC<CameraFeedProps> = ({ cameraId, cameraName, className = '' }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  const streamUrl = api.cameras.getStream(cameraId);

  useEffect(() => {
    // Initialize loading state for new camera
    setIsLoading(true);
    setError(null);
  }, [cameraId]);

  const handleImageLoad = () => {
    setIsLoading(false);
    setError(null);
  };

  const handleImageError = () => {
    setIsLoading(false);
    setError('Failed to load camera feed');
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const refreshFeed = () => {
    if (imgRef.current) {
      const currentSrc = imgRef.current.src;
      imgRef.current.src = '';
      imgRef.current.src = currentSrc;
      setIsLoading(true);
      setError(null);
    }
  };

  return (
    <>
      <div className={`relative bg-gray-900 rounded-lg overflow-hidden ${className}`}>
        {/* Camera Header */}
        <div className="absolute top-0 left-0 right-0 bg-gradient-to-b from-black/70 to-transparent p-2 sm:p-3 z-10">
          <div className="flex justify-between items-center">
            <h3 className="text-white font-medium text-sm sm:text-base">{cameraName}</h3>
            <div className="flex gap-1 sm:gap-2">
              <button
                onClick={refreshFeed}
                className="text-white hover:text-gray-300 transition-colors p-1 sm:p-0"
                title="Refresh feed"
              >
                <span className="text-base sm:text-lg">🔄</span>
              </button>
              <button
                onClick={toggleFullscreen}
                className="text-white hover:text-gray-300 transition-colors p-1 sm:p-0"
                title="Fullscreen"
              >
                <span className="text-base sm:text-lg">🔳</span>
              </button>
            </div>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-white text-center">
              <div className="animate-spin rounded-full h-8 w-8 sm:h-12 sm:w-12 border-b-2 border-white mx-auto"></div>
              <p className="mt-2 text-xs sm:text-sm">Loading feed...</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-white p-4">
              <p className="text-red-400 mb-2">⚠️ {error}</p>
              <button
                onClick={refreshFeed}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Camera Feed */}
        <img
          ref={imgRef}
          src={streamUrl}
          alt={`${cameraName} feed`}
          className="w-full h-full object-cover"
          onLoad={handleImageLoad}
          onError={handleImageError}
        />

        {/* Status Indicator */}
        <div className="absolute bottom-2 left-2 sm:bottom-3 sm:left-3 flex items-center gap-1 sm:gap-2">
          <div className={`w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full ${error ? 'bg-red-500' : 'bg-green-500'} animate-pulse`}></div>
          <span className="text-white text-xs">
            {error ? 'Offline' : 'Live'}
          </span>
        </div>
      </div>

      {/* Fullscreen Modal */}
      {isFullscreen && (
        <div 
          className="fixed inset-0 bg-black z-50 flex items-center justify-center"
          onClick={toggleFullscreen}
        >
          <img
            src={streamUrl}
            alt={`${cameraName} feed`}
            className="max-w-full max-h-full object-contain"
          />
          <button
            onClick={toggleFullscreen}
            className="absolute top-2 right-2 sm:top-4 sm:right-4 text-white text-xl sm:text-2xl hover:text-gray-300 p-2"
          >
            ✕
          </button>
        </div>
      )}
    </>
  );
};

export default CameraFeed;