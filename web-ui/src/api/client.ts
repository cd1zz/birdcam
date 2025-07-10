import axios from 'axios';

// API endpoints configuration
const PI_SERVER = 'http://localhost:8090';
const PROCESSING_SERVER = 'http://localhost:8091';

// Create axios instances for each server
export const piApi = axios.create({
  baseURL: PI_SERVER,
  timeout: 30000,
});

export const processingApi = axios.create({
  baseURL: PROCESSING_SERVER,
  timeout: 30000,
});

// Types for API responses
export interface Camera {
  id: string;
  name: string;
  resolution: string;
  status: 'active' | 'inactive';
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
  min_area: number;
  max_area: number;
  motion_timeout: number;
  pre_capture_seconds: number;
  post_capture_seconds: number;
  regions: Array<{
    id: string;
    name: string;
    points: Array<[number, number]>;
    enabled: boolean;
  }>;
}

// API functions
export const api = {
  // Pi Camera APIs
  cameras: {
    list: () => piApi.get<Camera[]>('/api/cameras'),
    getStream: (cameraId: string) => `${PI_SERVER}/api/camera/${cameraId}/stream`,
    getSnapshot: (cameraId: string) => `${PI_SERVER}/api/camera/${cameraId}/snapshot`,
  },

  // Motion settings
  motion: {
    getSettings: () => piApi.get<MotionSettings>('/api/motion-settings'),
    updateSettings: (settings: Partial<MotionSettings>) => 
      piApi.post('/api/motion-settings', settings),
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
    }) => processingApi.get<Detection[]>('/api/recent-detections', { params }),
    
    getThumbnail: (path: string) => `${PROCESSING_SERVER}/thumbnails/${path}`,
    getVideo: (filename: string) => `${PROCESSING_SERVER}/videos/${filename}`,
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