import React, { useState, useRef, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface MotionBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  enabled: boolean;
}

interface InteractiveCameraFeedProps {
  cameraId: number;
  cameraName: string;
  className?: string;
  showMotionBox?: boolean;
  onMotionBoxChange?: (box: MotionBox) => void;
}

const InteractiveCameraFeed: React.FC<InteractiveCameraFeedProps> = ({ 
  cameraId, 
  cameraName, 
  className = '',
  showMotionBox = false,
  onMotionBoxChange
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [motionBox, setMotionBox] = useState<MotionBox>({
    x1: 100, y1: 100, x2: 300, y2: 200, enabled: true
  });
  const [isDragging, setIsDragging] = useState(false);
  const [dragMode, setDragMode] = useState<'move' | 'resize' | null>(null);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [originalBox, setOriginalBox] = useState<MotionBox>(motionBox);
  const [isEditMode, setIsEditMode] = useState(false);
  
  const imgRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const streamUrl = api.cameras.getStream(cameraId, showMotionBox);

  // Load motion settings on component mount
  useEffect(() => {
    const loadMotionSettings = async () => {
      try {
        const settings = await api.motion.getSettings(cameraId);
        if (settings) {
          setMotionBox({
            x1: settings.motion_box_x1 || 100,
            y1: settings.motion_box_y1 || 100,
            x2: settings.motion_box_x2 || 300,
            y2: settings.motion_box_y2 || 200,
            enabled: settings.motion_box_enabled !== false
          });
        }
      } catch (error) {
        console.error('Failed to load motion settings:', error);
      }
    };

    loadMotionSettings();
  }, [cameraId]);

  useEffect(() => {
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

  // Convert screen coordinates to image coordinates
  const screenToImageCoords = useCallback((screenX: number, screenY: number) => {
    if (!imgRef.current || !containerRef.current) return { x: screenX, y: screenY };
    
    const rect = imgRef.current.getBoundingClientRect();
    const containerRect = containerRef.current.getBoundingClientRect();
    
    const relativeX = screenX - containerRect.left;
    const relativeY = screenY - containerRect.top;
    
    // Convert to image coordinates (assuming image fills container)
    const imageX = (relativeX / rect.width) * 640; // Assuming 640px image width
    const imageY = (relativeY / rect.height) * 480; // Assuming 480px image height
    
    return { 
      x: Math.max(0, Math.min(640, imageX)), 
      y: Math.max(0, Math.min(480, imageY)) 
    };
  }, []);

  // Convert image coordinates to screen coordinates for display
  const imageToScreenCoords = useCallback((imageX: number, imageY: number) => {
    if (!imgRef.current || !containerRef.current) return { x: imageX, y: imageY };
    
    const rect = imgRef.current.getBoundingClientRect();
    
    const screenX = (imageX / 640) * rect.width;
    const screenY = (imageY / 480) * rect.height;
    
    return { x: screenX, y: screenY };
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (!isEditMode) return;
    
    e.preventDefault();
    const coords = screenToImageCoords(e.clientX, e.clientY);
    
    // Check if clicking on resize handle (bottom-right corner)
    const screenBox = {
      x1: imageToScreenCoords(motionBox.x1, motionBox.y1).x,
      y1: imageToScreenCoords(motionBox.x1, motionBox.y1).y,
      x2: imageToScreenCoords(motionBox.x2, motionBox.y2).x,
      y2: imageToScreenCoords(motionBox.x2, motionBox.y2).y,
    };
    
    const handleSize = 10;
    const isOnResizeHandle = (
      Math.abs(e.clientX - (screenBox.x2 + (containerRef.current?.getBoundingClientRect().left || 0))) < handleSize &&
      Math.abs(e.clientY - (screenBox.y2 + (containerRef.current?.getBoundingClientRect().top || 0))) < handleSize
    );
    
    setIsDragging(true);
    setDragStart({ x: coords.x, y: coords.y });
    setOriginalBox({ ...motionBox });
    setDragMode(isOnResizeHandle ? 'resize' : 'move');
  }, [isEditMode, motionBox, screenToImageCoords, imageToScreenCoords]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging || !dragMode) return;
    
    const coords = screenToImageCoords(e.clientX, e.clientY);
    const deltaX = coords.x - dragStart.x;
    const deltaY = coords.y - dragStart.y;
    
    const newBox = { ...originalBox };
    
    if (dragMode === 'move') {
      // Move the entire box
      newBox.x1 = Math.max(0, Math.min(640 - (originalBox.x2 - originalBox.x1), originalBox.x1 + deltaX));
      newBox.y1 = Math.max(0, Math.min(480 - (originalBox.y2 - originalBox.y1), originalBox.y1 + deltaY));
      newBox.x2 = newBox.x1 + (originalBox.x2 - originalBox.x1);
      newBox.y2 = newBox.y1 + (originalBox.y2 - originalBox.y1);
    } else if (dragMode === 'resize') {
      // Resize from bottom-right corner
      newBox.x2 = Math.max(originalBox.x1 + 50, Math.min(640, originalBox.x2 + deltaX));
      newBox.y2 = Math.max(originalBox.y1 + 50, Math.min(480, originalBox.y2 + deltaY));
    }
    
    setMotionBox(newBox);
  }, [isDragging, dragMode, dragStart, originalBox, screenToImageCoords]);

  const saveMotionBox = useCallback(async (box: MotionBox) => {
    try {
      await api.motion.updateSettings({
        motion_box_enabled: box.enabled,
        motion_box_x1: Math.round(box.x1),
        motion_box_y1: Math.round(box.y1),
        motion_box_x2: Math.round(box.x2),
        motion_box_y2: Math.round(box.y2),
      }, cameraId);
      console.log('Motion box saved for camera', cameraId, ':', box);
    } catch (error) {
      console.error('Failed to save motion box:', error);
    }
  }, [cameraId]);

  const handleMouseUp = useCallback(() => {
    if (isDragging) {
      setIsDragging(false);
      setDragMode(null);
      
      // Save motion box to backend
      if (onMotionBoxChange) {
        onMotionBoxChange(motionBox);
      }
      
      saveMotionBox(motionBox);
    }
  }, [isDragging, motionBox, onMotionBoxChange, saveMotionBox]);

  const toggleMotionBox = () => {
    const newBox = { ...motionBox, enabled: !motionBox.enabled };
    setMotionBox(newBox);
    if (onMotionBoxChange) {
      onMotionBoxChange(newBox);
    }
    saveMotionBox(newBox);
  };

  const resetMotionBox = () => {
    const defaultBox = { x1: 100, y1: 100, x2: 300, y2: 200, enabled: true };
    setMotionBox(defaultBox);
    if (onMotionBoxChange) {
      onMotionBoxChange(defaultBox);
    }
    saveMotionBox(defaultBox);
  };

  // Add event listeners for mouse events on document
  useEffect(() => {
    const handleDocumentMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        handleMouseMove(e as unknown as React.MouseEvent<HTMLElement>);
      }
    };

    const handleDocumentMouseUp = () => {
      handleMouseUp();
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleDocumentMouseMove);
      document.addEventListener('mouseup', handleDocumentMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleDocumentMouseMove);
      document.removeEventListener('mouseup', handleDocumentMouseUp);
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  const renderMotionBoxOverlay = () => {
    if (!showMotionBox || !motionBox.enabled) return null;

    const screenCoords1 = imageToScreenCoords(motionBox.x1, motionBox.y1);
    const screenCoords2 = imageToScreenCoords(motionBox.x2, motionBox.y2);

    const width = screenCoords2.x - screenCoords1.x;
    const height = screenCoords2.y - screenCoords1.y;

    return (
      <div
        className={`absolute border-2 ${isEditMode ? 'border-green-400 cursor-move' : 'border-green-500'} bg-green-500 bg-opacity-20 pointer-events-${isEditMode ? 'auto' : 'none'}`}
        style={{
          left: `${screenCoords1.x}px`,
          top: `${screenCoords1.y}px`,
          width: `${width}px`,
          height: `${height}px`,
        }}
        onMouseDown={handleMouseDown}
      >
        {isEditMode && (
          <>
            {/* Resize handle */}
            <div
              className="absolute w-3 h-3 bg-green-400 border border-white cursor-nw-resize"
              style={{ right: '-6px', bottom: '-6px' }}
            />
            {/* Motion box label */}
            <div className="absolute -top-6 left-0 bg-green-500 text-white text-xs px-2 py-1 rounded">
              Motion Detection Area
            </div>
          </>
        )}
      </div>
    );
  };

  return (
    <>
      <div className={`relative bg-gray-900 rounded-lg overflow-hidden ${className}`}>
        {/* Camera Header */}
        <div className="absolute top-0 left-0 right-0 bg-gradient-to-b from-black/70 to-transparent p-3 z-20">
          <div className="flex justify-between items-center">
            <h3 className="text-white font-medium">{cameraName}</h3>
            <div className="flex gap-2">
              {showMotionBox && (
                <>
                  <button
                    onClick={() => setIsEditMode(!isEditMode)}
                    className={`px-2 py-1 text-xs rounded ${isEditMode ? 'bg-green-600 text-white' : 'bg-gray-600 text-white'} hover:bg-green-700 transition-colors`}
                    title="Edit motion box"
                  >
                    {isEditMode ? 'Done' : 'Edit'}
                  </button>
                  <button
                    onClick={toggleMotionBox}
                    className={`px-2 py-1 text-xs rounded ${motionBox.enabled ? 'bg-green-600 text-white' : 'bg-red-600 text-white'} hover:opacity-80 transition-opacity`}
                    title={motionBox.enabled ? 'Disable motion detection' : 'Enable motion detection'}
                  >
                    {motionBox.enabled ? 'ON' : 'OFF'}
                  </button>
                  <button
                    onClick={resetMotionBox}
                    className="px-2 py-1 text-xs rounded bg-gray-600 text-white hover:bg-gray-700 transition-colors"
                    title="Reset motion box"
                  >
                    Reset
                  </button>
                </>
              )}
              <button
                onClick={refreshFeed}
                className="text-white hover:text-gray-300 transition-colors"
                title="Refresh feed"
              >
                🔄
              </button>
              <button
                onClick={toggleFullscreen}
                className="text-white hover:text-gray-300 transition-colors"
                title="Fullscreen"
              >
                🔳
              </button>
            </div>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="text-white">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
              <p className="mt-2 text-sm">Loading feed...</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
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

        {/* Camera Feed Container */}
        <div 
          ref={containerRef}
          className="relative w-full h-full"
          style={{ cursor: isEditMode && showMotionBox ? 'crosshair' : 'default' }}
        >
          {/* Camera Feed */}
          <img
            ref={imgRef}
            src={streamUrl}
            alt={`${cameraName} feed`}
            className="w-full h-full object-cover"
            onLoad={handleImageLoad}
            onError={handleImageError}
            draggable={false}
          />

          {/* Motion Box Overlay */}
          {renderMotionBoxOverlay()}
        </div>

        {/* Status Indicator */}
        <div className="absolute bottom-3 left-3 flex items-center gap-2 z-10">
          <div className={`w-2 h-2 rounded-full ${error ? 'bg-red-500' : 'bg-green-500'} animate-pulse`}></div>
          <span className="text-white text-xs">
            {error ? 'Offline' : 'Live'}
          </span>
          {showMotionBox && (
            <span className="text-white text-xs ml-2">
              Motion: {motionBox.enabled ? 'ON' : 'OFF'}
            </span>
          )}
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
            className="absolute top-4 right-4 text-white text-2xl hover:text-gray-300"
          >
            ✕
          </button>
        </div>
      )}
    </>
  );
};

export default InteractiveCameraFeed;