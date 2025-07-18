import { createContext, useContext, useState, useEffect } from 'react';
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
  
  // Check for existing session on mount
  useEffect(() => {
    const initAuth = async () => {
      const accessToken = localStorage.getItem('accessToken');
      if (accessToken) {
        setAuthToken(accessToken);
        try {
          const response = await apiClient.get('/api/auth/me');
          setUser(response.data);
        } catch (error) {
          // Token invalid, clear it
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          setAuthToken(null);
        }
      }
      setIsLoading(false);
    };
    
    initAuth();
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
  };
  
  const refreshToken = async () => {
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }
    
    const response = await apiClient.post('/api/auth/refresh', {
      refresh_token: refreshToken
    });
    
    const { access_token, refresh_token: newRefreshToken } = response.data;
    
    // Store new tokens
    localStorage.setItem('accessToken', access_token);
    localStorage.setItem('refreshToken', newRefreshToken);
    
    // Configure API authentication
    setAuthToken(access_token);
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