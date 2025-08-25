import { createContext } from 'react';

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

export const AuthContext = createContext<AuthContextType | undefined>(undefined);
export type { User, AuthContextType };