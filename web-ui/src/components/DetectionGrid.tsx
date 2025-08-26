import React from 'react';
import { type Detection, api } from '../api/client';

interface DetectionGridProps {
  detections: Detection[];
  onVideoClick?: (detection: Detection) => void;
}

const DetectionGrid: React.FC<DetectionGridProps> = ({ detections, onVideoClick }) => {
  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getSpeciesEmoji = (species: string) => {
    const emojiMap: { [key: string]: string } = {
      bird: '🦜',
      cat: '🐱',
      dog: '🐕',
      person: '👤',
      raccoon: '🦝',
      squirrel: '🐿️',
      default: '🐾'
    };
    return emojiMap[species.toLowerCase()] || emojiMap.default;
  };

  if (detections.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400 text-lg">No detections found</p>
        <p className="text-gray-400 dark:text-gray-500 text-sm mt-2">
          Wildlife will appear here when detected by the cameras
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-4">
      {detections.map((detection) => (
        <div
          key={detection.id}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden cursor-pointer hover:shadow-lg transition-shadow"
          onClick={() => onVideoClick?.(detection)}
        >
          {/* Thumbnail */}
          <div className="relative aspect-video bg-gray-200 dark:bg-gray-700">
            {(detection.thumbnail || detection.thumbnail_path) ? (
              <img
                src={api.detections.getThumbnail(detection.thumbnail || detection.thumbnail_path || '')}
                alt={`${detection.species} detection`}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                }}
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <span className="text-4xl">{getSpeciesEmoji(detection.species)}</span>
              </div>
            )}
            
            {/* Confidence Badge */}
            <div className="absolute top-1 right-1 sm:top-2 sm:right-2 bg-black/70 text-white px-1.5 py-0.5 sm:px-2 sm:py-1 rounded text-xs">
              {(detection.confidence * 100).toFixed(0)}%
            </div>

            {/* Event Badge */}
            {detection.event_id && (
              <div className="absolute top-1 left-1 sm:top-2 sm:left-2 bg-blue-600 text-white px-1.5 py-0.5 sm:px-2 sm:py-1 rounded text-xs">
                Event
              </div>
            )}
          </div>

          {/* Details */}
          <div className="p-3 sm:p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-base sm:text-lg capitalize flex items-center gap-1 sm:gap-2 text-gray-900 dark:text-white">
                <span className="text-base sm:text-lg">{getSpeciesEmoji(detection.species)}</span>
                <span className="truncate">
                  {detection.species}
                  {detection.count && detection.count > 1 && ` (x${detection.count})`}
                </span>
              </h3>
              {detection.duration && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {detection.duration}s
                </span>
              )}
            </div>
            
            <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-300 mb-1">
              {formatDate(detection.received_time || detection.timestamp || '')}
            </p>
            
            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
              {detection.filename || detection.video_path?.split('/').pop() || 'No file'}
            </p>

            {/* Play Button */}
            <button className="mt-2 sm:mt-3 w-full bg-blue-600 dark:bg-blue-700 text-white py-1.5 sm:py-2 rounded hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors flex items-center justify-center gap-2 text-sm sm:text-base">
              <span>▶️</span>
              <span className="hidden sm:inline">Play Video</span>
              <span className="sm:hidden">Play</span>
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default DetectionGrid;