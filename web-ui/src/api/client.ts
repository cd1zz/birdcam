import axios from 'axios';

// API endpoints configuration
const PI_SERVER = import.meta.env.VITE_PI_SERVER || 'http://localhost:8090';
const PROCESSING_SERVER = import.meta.env.VITE_PROCESSING_SERVER || '';

// Create axios instances
export const piApi = axios.create({
  baseURL: PI_SERVER,
  timeout: 30000,
});

export const processingApi = axios.create({
  baseURL: PROCESSING_SERVER || '',
  timeout: 30000,
});

// Core types
export interface Camera {
  id: number;
  name: string;
  is_active: boolean;
  sensor_type: string;
}

export interface Detection {
  id: number;
  video_path?: string; // Legacy field
  filename: string; // Primary filename field
  timestamp?: string; // Legacy field  
  received_time: string; // Primary timestamp field
  species: string;
  confidence: number;
  bounding_box?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  thumbnail_path?: string; // Legacy field
  thumbnail?: string; // Primary thumbnail field
  event_id?: string;
  count?: number; // For clustered events
  duration?: number;
}

export interface SystemStatus {
  status: string;
  uptime: number;
  cameras_active: number;
  videos_today: number;
  detections_today: number;
  storage_used: number;
  storage_total: number;
  queue?: {
    pending: number;
    processing: number;
    failed: number;
    is_processing: boolean;
  };
  performance?: {
    processing_rate_hour: number;
    processing_rate_day: number;
    avg_processing_time: number;
    detection_rate: number;
    session_processed: number;
    session_failed: number;
  };
  system?: {
    cpu_percent: number;
    memory_percent: number;
    model_loaded: boolean;
  };
  totals?: {
    videos_processed: number;
    total_detections: number;
    videos_with_detections: number;
  };
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

export interface SystemSettings {
  storage: {
    storage_path: string;
  };
  detection: {
    classes: string[];
    confidences: Record<string, number>;
    model_name: string;
    process_every_nth_frame: number;
    max_thumbnails_per_video: number;
  };
  retention: {
    detection_retention_days: number;
    no_detection_retention_days: number;
  };
  sync: {
    sync_interval_minutes: number;
    upload_timeout_seconds: number;
  };
}

// API functions with consistent response handling
export const api = {
  // Pi Camera APIs
  cameras: {
    list: async (): Promise<Camera[]> => {
      const response = await piApi.get<{cameras: Camera[]}>('/api/cameras');
      return response.data.cameras;
    },
    getStream: (cameraId: number) => `${PI_SERVER}/api/camera/${cameraId}/stream`,
    getSnapshot: (cameraId: number) => `${PI_SERVER}/api/camera/${cameraId}/snapshot`,
  },

  // Motion settings
  motion: {
    getSettings: async (cameraId?: number): Promise<MotionSettings> => {
      const response = await processingApi.get<MotionSettings>('/api/motion-settings', { 
        params: cameraId !== undefined ? { camera_id: cameraId } : undefined 
      });
      return response.data;
    },
    
    updateSettings: async (settings: Partial<MotionSettings>, cameraId?: number): Promise<void> => {
      await processingApi.post('/api/motion-settings', settings, { 
        params: cameraId !== undefined ? { camera_id: cameraId } : undefined 
      });
    },
    
    getActivePassiveConfig: async () => {
      const response = await piApi.get('/api/active-passive/config');
      return response.data;
    },
    
    getActivePassiveStats: async () => {
      const response = await piApi.get('/api/active-passive/stats');
      return response.data;
    },
    
    testActivePassiveTrigger: async () => {
      const response = await piApi.get('/api/active-passive/test-trigger');
      return response.data;
    },
  },

  // System status
  status: {
    getPiStatus: async (): Promise<SystemStatus> => {
      const response = await piApi.get<SystemStatus>('/api/status');
      return response.data;
    },
    
    getProcessingStatus: async (): Promise<SystemStatus> => {
      const response = await processingApi.get<SystemStatus>('/api/status');
      return response.data;
    },
  },

  // Detection APIs
  detections: {
    getRecent: async (params?: {
      limit?: number;
      species?: string;
      start?: string;
      end?: string;
      sort?: 'asc' | 'desc';
    }): Promise<Detection[]> => {
      const response = await processingApi.get<{detections: Detection[]}>('/api/recent-detections', { params });
      return response.data.detections;
    },
    
    getThumbnail: (path: string) => `${PROCESSING_SERVER || ''}/thumbnails/${path}`,
    getVideo: (filename: string) => `${PROCESSING_SERVER || ''}/videos/${filename}`,
  },

  // Video processing
  processing: {
    processVideo: async (videoPath: string): Promise<void> => {
      await processingApi.post('/api/process-video', { video_path: videoPath });
    },
    
    // Manual triggers
    triggerProcessing: async (): Promise<void> => {
      await processingApi.post('/api/process-now');
    },
    
    triggerCleanup: async (): Promise<void> => {
      await processingApi.post('/api/cleanup-now');
    },
  },

  // System operations
  system: {
    // Manual sync from Pi to processing server
    triggerSync: async (): Promise<void> => {
      await piApi.post('/api/sync-now');
    },
    
    // Trigger processing via Pi (proxy to processing server)
    triggerRemoteProcessing: async (): Promise<void> => {
      await piApi.post('/api/process-server-queue');
    },
    
    // System settings
    getSettings: async (): Promise<SystemSettings> => {
      const response = await processingApi.get<SystemSettings>('/api/system-settings');
      return response.data;
    },
    
    updateSettings: async (settings: Partial<SystemSettings>): Promise<{success: boolean; warning?: string}> => {
      const response = await processingApi.post<{success: boolean; warning?: string}>('/api/system-settings', settings);
      return response.data;
    },
  },
};

// Enhanced error handling interceptors
piApi.interceptors.response.use(
  response => response,
  error => {
    console.error('Pi API Error:', {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
      url: error.config?.url
    });
    
    // Add user-friendly error messages
    if (error.code === 'ECONNREFUSED') {
      error.userMessage = 'Cannot connect to Pi camera system. Please check if it\'s running.';
    } else if (error.response?.status === 404) {
      error.userMessage = 'Requested resource not found.';
    } else if (error.response?.status >= 500) {
      error.userMessage = 'Pi camera system error. Please try again.';
    }
    
    return Promise.reject(error);
  }
);

processingApi.interceptors.response.use(
  response => response,
  error => {
    console.error('Processing API Error:', {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
      url: error.config?.url
    });
    
    // Add user-friendly error messages
    if (error.code === 'ECONNREFUSED') {
      error.userMessage = 'Cannot connect to AI processing server. Please check if it\'s running.';
    } else if (error.response?.status === 404) {
      error.userMessage = 'Requested resource not found.';
    } else if (error.response?.status >= 500) {
      error.userMessage = 'AI processing server error. Please try again.';
    }
    
    return Promise.reject(error);
  }
);