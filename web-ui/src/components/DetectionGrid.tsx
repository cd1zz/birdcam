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
      bird: '🦅',
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
        <p className="text-gray-500 text-lg">No detections found</p>
        <p className="text-gray-400 text-sm mt-2">
          Wildlife will appear here when detected by the cameras
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {detections.map((detection) => (
        <div
          key={detection.id}
          className="bg-white rounded-lg shadow-md overflow-hidden cursor-pointer hover:shadow-lg transition-shadow"
          onClick={() => onVideoClick?.(detection)}
        >
          {/* Thumbnail */}
          <div className="relative aspect-video bg-gray-200">
            {detection.thumbnail_path ? (
              <img
                src={api.detections.getThumbnail(detection.thumbnail_path)}
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
            <div className="absolute top-2 right-2 bg-black/70 text-white px-2 py-1 rounded text-xs">
              {(detection.confidence * 100).toFixed(0)}%
            </div>

            {/* Event Badge */}
            {detection.event_id && (
              <div className="absolute top-2 left-2 bg-blue-600 text-white px-2 py-1 rounded text-xs">
                Event
              </div>
            )}
          </div>

          {/* Details */}
          <div className="p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-lg capitalize flex items-center gap-2">
                <span>{getSpeciesEmoji(detection.species)}</span>
                {detection.species}
              </h3>
            </div>
            
            <p className="text-sm text-gray-600 mb-1">
              {formatDate(detection.timestamp)}
            </p>
            
            <p className="text-xs text-gray-500">
              {detection.video_path.split('/').pop()}
            </p>

            {/* Play Button */}
            <button className="mt-3 w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition-colors flex items-center justify-center gap-2">
              <span>▶️</span>
              <span>Play Video</span>
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default DetectionGrid;