import axios from 'axios';

// API endpoints configuration
// When VITE_PROCESSING_SERVER is not set, use relative paths (same origin)
const PROCESSING_SERVER = import.meta.env.VITE_PROCESSING_SERVER || '';
// For Pi server, we can now use proxy endpoints through the processing server
const PI_SERVER = import.meta.env.VITE_PI_SERVER || '';
// Check if we should use proxy mode (when PI_SERVER is not set, use processing server proxy)
const USE_PI_PROXY = !PI_SERVER && !import.meta.env.VITE_PI_SERVER;

// Helper function to ensure HTTPS when the page is loaded over HTTPS
function ensureHttps(url: string): string {
  if (!url) return url;
  
  try {
    // Check if URL contains a private/local IP address
    const urlObj = new URL(url);
    const hostname = urlObj.hostname;
    
    // Regular expressions for private IP ranges
    const privateIPRegex = /^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.|127\.|localhost)/;
    
    // If it's a private IP or localhost, keep it as HTTP
    if (privateIPRegex.test(hostname)) {
      return url;
    }
  } catch (e) {
    // If URL parsing fails, continue with simple string replacement
  }
  
  // If the current page is HTTPS and the URL is HTTP, convert it
  if (window.location.protocol === 'https:' && url.startsWith('http://')) {
    return url.replace('http://', 'https://');
  }
  
  return url;
}

// Create axios instances
// When USE_PI_PROXY is true, use processingApi for all Pi endpoints
export const piApi = USE_PI_PROXY ? axios.create({
  baseURL: ensureHttps(PROCESSING_SERVER),
  timeout: 30000,
}) : axios.create({
  baseURL: ensureHttps(PI_SERVER),
  timeout: 30000,
});

export const processingApi = axios.create({
  baseURL: ensureHttps(PROCESSING_SERVER), // Empty string means relative paths
  timeout: 30000,
});

// API client for auth (uses processing server)
export const apiClient = processingApi;

// Function to set auth token on all axios instances
export function setAuthToken(token: string | null) {
  if (token) {
    piApi.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    processingApi.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete piApi.defaults.headers.common['Authorization'];
    delete processingApi.defaults.headers.common['Authorization'];
  }
}

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
      const endpoint = USE_PI_PROXY ? '/api/pi/cameras' : '/api/cameras';
      const response = await piApi.get<{cameras: Camera[]}>(endpoint);
      return response.data.cameras;
    },
    getStream: (cameraId: number, showMotionBox = false) => {
      const token = localStorage.getItem('accessToken');
      const params = new URLSearchParams();
      
      if (USE_PI_PROXY && token) {
        params.append('token', token);
      }
      
      if (showMotionBox) {
        params.append('show_motion_box', 'true');
      }
      
      const queryString = params.toString() ? `?${params.toString()}` : '';
      
      if (USE_PI_PROXY) {
        return PROCESSING_SERVER ? ensureHttps(`${PROCESSING_SERVER}/api/pi/camera/${cameraId}/stream${queryString}`) : `/api/pi/camera/${cameraId}/stream${queryString}`;
      }
      return PI_SERVER ? ensureHttps(`${PI_SERVER}/api/camera/${cameraId}/stream${queryString}`) : `/api/camera/${cameraId}/stream${queryString}`;
    },
    getSnapshot: (cameraId: number, showMotionBox = false) => {
      const token = localStorage.getItem('accessToken');
      const params = new URLSearchParams();
      
      if (USE_PI_PROXY && token) {
        params.append('token', token);
      }
      
      if (showMotionBox) {
        params.append('show_motion_box', 'true');
      }
      
      const queryString = params.toString() ? `?${params.toString()}` : '';
      
      if (USE_PI_PROXY) {
        return PROCESSING_SERVER ? ensureHttps(`${PROCESSING_SERVER}/api/pi/camera/${cameraId}/snapshot${queryString}`) : `/api/pi/camera/${cameraId}/snapshot${queryString}`;
      }
      return PI_SERVER ? ensureHttps(`${PI_SERVER}/api/camera/${cameraId}/snapshot${queryString}`) : `/api/camera/${cameraId}/snapshot${queryString}`;
    },
  },

  // Motion settings
  motion: {
    getSettings: async (cameraId?: number): Promise<MotionSettings> => {
      // Motion settings should come from Pi when camera is specified
      if (cameraId !== undefined && USE_PI_PROXY) {
        const response = await piApi.get<MotionSettings>('/api/pi/motion-settings', { 
          params: { camera_id: cameraId }
        });
        return response.data;
      }
      const response = await processingApi.get<MotionSettings>('/api/motion-settings', { 
        params: cameraId !== undefined ? { camera_id: cameraId } : undefined 
      });
      return response.data;
    },
    
    updateSettings: async (settings: Partial<MotionSettings>, cameraId?: number): Promise<void> => {
      // Motion settings should be sent to Pi when camera is specified
      if (cameraId !== undefined && USE_PI_PROXY) {
        await piApi.post('/api/pi/motion-settings', settings, { 
          params: { camera_id: cameraId }
        });
        return;
      }
      await processingApi.post('/api/motion-settings', settings, { 
        params: cameraId !== undefined ? { camera_id: cameraId } : undefined 
      });
    },
    
    getActivePassiveConfig: async () => {
      const endpoint = USE_PI_PROXY ? '/api/pi/active-passive/config' : '/api/active-passive/config';
      const response = await piApi.get(endpoint);
      return response.data;
    },
    
    getActivePassiveStats: async () => {
      const endpoint = USE_PI_PROXY ? '/api/pi/active-passive/stats' : '/api/active-passive/stats';
      const response = await piApi.get(endpoint);
      return response.data;
    },
    
    testActivePassiveTrigger: async () => {
      const endpoint = USE_PI_PROXY ? '/api/pi/active-passive/test-trigger' : '/api/active-passive/test-trigger';
      const response = await piApi.get(endpoint);
      return response.data;
    },
  },

  // System status
  status: {
    getPiStatus: async (): Promise<SystemStatus> => {
      const endpoint = USE_PI_PROXY ? '/api/pi/status' : '/api/status';
      const response = await piApi.get<SystemStatus>(endpoint);
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
    
    getThumbnail: (path: string) => PROCESSING_SERVER ? ensureHttps(`${PROCESSING_SERVER}/thumbnails/${path}`) : `/thumbnails/${path}`,
    getVideo: (filename: string) => PROCESSING_SERVER ? ensureHttps(`${PROCESSING_SERVER}/videos/${filename}`) : `/videos/${filename}`,
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
      const endpoint = USE_PI_PROXY ? '/api/pi/sync-now' : '/api/sync-now';
      await piApi.post(endpoint);
    },
    
    // Trigger processing via Pi (proxy to processing server)
    triggerRemoteProcessing: async (): Promise<void> => {
      const endpoint = USE_PI_PROXY ? '/api/pi/process-server-queue' : '/api/process-server-queue';
      await piApi.post(endpoint);
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

  // Logs APIs
  logs: {
    getPiCaptureLogs: async (params?: { lines?: number; since?: string; level?: string; search?: string }) => {
      const response = await processingApi.get('/api/logs/pi-capture', { params });
      return response.data;
    },
    getAiProcessorLogs: async (params?: { lines?: number; since?: string; level?: string; search?: string }) => {
      const response = await processingApi.get('/api/logs/ai-processor', { params });
      return response.data;
    },
    getRemotePiCaptureLogs: async (params?: { lines?: number; since?: string; level?: string; search?: string; hostname?: string }) => {
      const response = await processingApi.get('/api/logs/remote/pi-capture', { params });
      return response.data;
    },
    getCombinedLogs: async (params?: { lines?: number; since?: string; level?: string; search?: string; service?: string }) => {
      const response = await processingApi.get('/api/logs/combined', { params });
      return response.data;
    },
    getLogLevels: async () => {
      const response = await processingApi.get('/api/logs/levels');
      return response.data;
    },
    exportLogs: async (params?: { since?: string; service?: string; format?: string }) => {
      const response = await processingApi.get('/api/logs/export', { 
        params,
        responseType: 'blob' 
      });
      return response.data;
    },
  },
  
  // Raw API access for endpoints not yet wrapped
  get: processingApi.get.bind(processingApi),
  post: processingApi.post.bind(processingApi),
  put: processingApi.put.bind(processingApi),
  delete: processingApi.delete.bind(processingApi),
};

// Token refresh logic
let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  
  failedQueue = [];
};

// Enhanced error handling interceptors
piApi.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;
    
    // Handle 401 errors (unauthorized) - but not for refresh endpoint itself
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/api/auth/refresh')) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers['Authorization'] = 'Bearer ' + token;
          return piApi(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }
      
      originalRequest._retry = true;
      isRefreshing = true;
      
      const refreshToken = localStorage.getItem('refreshToken');
      
      if (refreshToken) {
        try {
          const response = await apiClient.post('/api/auth/refresh', {
            refresh_token: refreshToken
          });
          
          const { access_token, refresh_token: newRefreshToken } = response.data;
          localStorage.setItem('accessToken', access_token);
          localStorage.setItem('refreshToken', newRefreshToken);
          setAuthToken(access_token);
          
          processQueue(null, access_token);
          
          return piApi(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          // Clear tokens but don't redirect here - let AuthContext handle it
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          setAuthToken(null);
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }
    }
    
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
  async error => {
    const originalRequest = error.config;
    
    // Handle 401 errors (unauthorized) - but not for refresh endpoint itself
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/api/auth/refresh')) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers['Authorization'] = 'Bearer ' + token;
          return processingApi(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }
      
      originalRequest._retry = true;
      isRefreshing = true;
      
      const refreshToken = localStorage.getItem('refreshToken');
      
      if (refreshToken) {
        try {
          const response = await apiClient.post('/api/auth/refresh', {
            refresh_token: refreshToken
          });
          
          const { access_token, refresh_token: newRefreshToken } = response.data;
          localStorage.setItem('accessToken', access_token);
          localStorage.setItem('refreshToken', newRefreshToken);
          setAuthToken(access_token);
          
          processQueue(null, access_token);
          
          return processingApi(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          // Clear tokens but don't redirect here - let AuthContext handle it
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          setAuthToken(null);
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }
    }
    
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