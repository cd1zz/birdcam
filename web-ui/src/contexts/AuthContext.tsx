import { createContext, useContext, useState, useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { apiClient, setAuthToken } from '../api/client';

interface User {
  id: number;
  username: string;
  role: 'admin' | 'viewer';
  created_at: string;
  last_login: string | null;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const refreshIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  
  const refreshToken = async () => {
    const refreshTokenValue = localStorage.getItem('refreshToken');
    if (!refreshTokenValue) {
      throw new Error('No refresh token available');
    }
    
    const response = await apiClient.post('/api/auth/refresh', {
      refresh_token: refreshTokenValue
    });
    
    const { access_token, refresh_token: newRefreshToken } = response.data;
    
    // Store new tokens
    localStorage.setItem('accessToken', access_token);
    localStorage.setItem('refreshToken', newRefreshToken);
    
    // Configure API authentication
    setAuthToken(access_token);
  };
  
  // Check for existing session on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        const accessToken = localStorage.getItem('accessToken');
        const refreshTokenValue = localStorage.getItem('refreshToken');
        
        if (accessToken) {
          setAuthToken(accessToken);
          try {
            const response = await apiClient.get('/api/auth/me');
            setUser(response.data);
          } catch (error) {
            // If token is expired and we have a refresh token, try to refresh
            if ((error as any).response?.status === 401 && refreshTokenValue) {
              try {
                const refreshResponse = await apiClient.post('/api/auth/refresh', {
                  refresh_token: refreshTokenValue
                });
                
                const { access_token, refresh_token: newRefreshToken, user } = refreshResponse.data;
                
                // Store new tokens
                localStorage.setItem('accessToken', access_token);
                localStorage.setItem('refreshToken', newRefreshToken);
                
                // Set auth header
                setAuthToken(access_token);
                
                // Get user data if not included in refresh response
                if (user) {
                  setUser(user);
                } else {
                  const meResponse = await apiClient.get('/api/auth/me');
                  setUser(meResponse.data);
                }
              } catch (refreshError) {
                // Refresh failed, clear everything
                localStorage.removeItem('accessToken');
                localStorage.removeItem('refreshToken');
                setAuthToken(null);
                setUser(null);
                
                // If the refresh endpoint returns 401, it means the refresh token is also invalid
                // This ensures we properly clear the auth state and trigger navigation to login
                if ((refreshError as any).response?.status === 401) {
                  console.log('Refresh token is invalid, clearing auth state');
                }
              }
            } else {
              // No refresh token or other error, clear everything
              localStorage.removeItem('accessToken');
              localStorage.removeItem('refreshToken');
              setAuthToken(null);
              setUser(null);
            }
          }
        }
      } catch (error) {
        // Catch any unexpected errors
        console.error('Auth initialization error:', error);
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        setAuthToken(null);
        setUser(null);
      } finally {
        // Always set loading to false
        setIsLoading(false);
      }
    };
    
    initAuth();
  }, []);
  
  // Set up periodic token refresh (every 20 minutes, before the 30-minute expiry)
  useEffect(() => {
    if (user && localStorage.getItem('refreshToken')) {
      // Clear any existing interval
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
      
      // Set up new interval
      refreshIntervalRef.current = setInterval(async () => {
        try {
          await refreshToken();
        } catch (error) {
          console.error('Periodic token refresh failed:', error);
        }
      }, 20 * 60 * 1000); // 20 minutes
      
      // Cleanup on unmount or when user changes
      return () => {
        if (refreshIntervalRef.current) {
          clearInterval(refreshIntervalRef.current);
          refreshIntervalRef.current = null;
        }
      };
    }
  }, [user]);
  
  // Listen for storage changes to handle token removal from interceptors
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'accessToken' && !e.newValue) {
        // Access token was removed, clear user state
        setUser(null);
        setAuthToken(null);
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);
  
  const login = async (username: string, password: string) => {
    const response = await apiClient.post('/api/auth/login', {
      username,
      password
    });
    
    const { access_token, refresh_token, user } = response.data;
    
    // Store tokens
    localStorage.setItem('accessToken', access_token);
    localStorage.setItem('refreshToken', refresh_token);
    
    // Set auth header
    setAuthToken(access_token);
    
    // Set user
    setUser(user);
  };
  
  const logout = () => {
    // Clear tokens
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    
    // Clear auth header
    setAuthToken(null);
    
    // Clear user
    setUser(null);
    
    // Clear refresh interval
    if (refreshIntervalRef.current) {
      clearInterval(refreshIntervalRef.current);
      refreshIntervalRef.current = null;
    }
  };
  
  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    refreshToken
  };
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}