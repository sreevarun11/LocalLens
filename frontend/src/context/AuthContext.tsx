import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

export interface User {
  id: string;
  email: string;
  display_name: string;
  is_email_verified: boolean;
  created_at: string;
}

export interface UserCredits {
  credits_remaining: number;
  credits_used: number;
  can_generate_report: boolean;
}

interface AuthContextType {
  user: User | null;
  credits: UserCredits | null;
  token: string | null;
  isAuthenticated: boolean;
  isEmailVerified: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
  verifyEmailSimulate: () => Promise<void>;
  resendVerification: () => Promise<string>;
  refreshCredits: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [credits, setCredits] = useState<UserCredits | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('locallens_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initial user load if token present
  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      return;
    }

    api.getMe()
      .then((data) => {
        setUser(data.user);
        setCredits(data.credits);
      })
      .catch(() => {
        // Expired or invalid token
        localStorage.removeItem('locallens_token');
        setToken(null);
        setUser(null);
        setCredits(null);
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const data = await api.login(email, password);
      localStorage.setItem('locallens_token', data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      try {
        const creds = await api.getCredits();
        setCredits(creds);
      } catch (err) {
        console.warn('Credits load deferred:', err);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, displayName?: string) => {
    setIsLoading(true);
    try {
      const data = await api.register(email, password, displayName);
      localStorage.setItem('locallens_token', data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      try {
        const creds = await api.getCredits();
        setCredits(creds);
      } catch (err) {
        console.warn('Credits load deferred:', err);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('locallens_token');
    setToken(null);
    setUser(null);
    setCredits(null);
  };

  const verifyEmailSimulate = async () => {
    const res = await api.verifyEmailSimulate();
    if (res.access_token) {
      localStorage.setItem('locallens_token', res.access_token);
      setToken(res.access_token);
    }
    setUser(res.user);
    setCredits(res.credits);
  };

  const resendVerification = async (): Promise<string> => {
    const res = await api.resendVerification();
    return res.message;
  };

  const refreshCredits = async () => {
    if (!token) return;
    try {
      const creds = await api.getCredits();
      setCredits(creds);
    } catch (e) {
      console.error('Failed to refresh credits:', e);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        credits,
        token,
        isAuthenticated: !!user,
        isEmailVerified: !!user?.is_email_verified,
        isLoading,
        login,
        register,
        logout,
        verifyEmailSimulate,
        resendVerification,
        refreshCredits
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
