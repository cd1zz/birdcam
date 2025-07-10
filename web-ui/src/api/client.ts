import axios from 'axios';

// API endpoints configuration
// Use environment variables with sensible fallbacks
const PI_SERVER = import.meta.env.VITE_PI_SERVER || 'http://localhost:8090';
const PROCESSING_SERVER = import.meta.env.VITE_PROCESSING_SERVER || '';

// Create axios instances for each server
export const piApi = axios.create({
  baseURL: PI_SERVER,
  timeout: 30000,
});

export const processingApi = axios.create({
  baseURL: PROCESSING_SERVER || '', // Empty string uses relative URLs
  timeout: 30000,
});

// Types for API responses
export interface Camera {
  id: number;
  name: string;
  is_active: boolean;
  sensor_type: string;
}

export interface Detection {
  id: number;
  video_path: string;
  timestamp: string;
  species: string;
  confidence: number;
  bounding_box: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  thumbnail_path?: string;
  event_id?: string;
}

export interface SystemStatus {
  status: string;
  uptime: number;
  cameras_active: number;
  videos_today: number;
  detections_today: number;
  storage_used: number;
  storage_total: number;
}

export interface MotionSettings {
  motion_threshold: number;
  min_contour_area: number;
  motion_timeout_seconds: number;
  motion_box_enabled: boolean;
  motion_box_x1: number;
  motion_box_y1: number;
  motion_box_x2: number;
  motion_box_y2: number;
  region?: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  };
}

// API functions
export const api = {
  // Pi Camera APIs
  cameras: {
    list: () => piApi.get<{cameras: Camera[]}>('/api/cameras'),
    getStream: (cameraId: number) => `${PI_SERVER}/api/camera/${cameraId}/stream`,
    getSnapshot: (cameraId: number) => `${PI_SERVER}/api/camera/${cameraId}/snapshot`,
  },

  // Motion settings
  motion: {
    getSettings: (cameraId?: number) => 
      piApi.get<MotionSettings>('/api/motion-settings', { 
        params: cameraId !== undefined ? { camera_id: cameraId } : undefined 
      }),
    updateSettings: (settings: Partial<MotionSettings>, cameraId?: number) => 
      piApi.post('/api/motion-settings', settings, { 
        params: cameraId !== undefined ? { camera_id: cameraId } : undefined 
      }),
    getBroadcasterConfig: () => piApi.get('/api/motion-broadcaster/config'),
    updateBroadcasterConfig: (config: any) => 
      piApi.post('/api/motion-broadcaster/config', config),
  },

  // System status
  status: {
    getPiStatus: () => piApi.get<SystemStatus>('/api/status'),
    getProcessingStatus: () => processingApi.get<SystemStatus>('/api/status'),
  },

  // Detection APIs
  detections: {
    getRecent: (params?: {
      limit?: number;
      species?: string;
      start?: string;
      end?: string;
      sort?: 'asc' | 'desc';
    }) => processingApi.get<{detections: Detection[]}>('/api/recent-detections', { params }),
    
    getThumbnail: (path: string) => `${PROCESSING_SERVER || ''}/thumbnails/${path}`,
    getVideo: (filename: string) => `${PROCESSING_SERVER || ''}/videos/${filename}`,
  },

  // Video processing
  processing: {
    processVideo: (videoPath: string) => 
      processingApi.post('/api/process-video', { video_path: videoPath }),
  },
};

// Error handling interceptors
piApi.interceptors.response.use(
  response => response,
  error => {
    console.error('Pi API Error:', error.message);
    return Promise.reject(error);
  }
);

processingApi.interceptors.response.use(
  response => response,
  error => {
    console.error('Processing API Error:', error.message);
    return Promise.reject(error);
  }
);