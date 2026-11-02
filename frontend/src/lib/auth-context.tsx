'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { api, clearToken, getToken, setToken, UserResponse, UserLoginInput, UserRegisterInput } from './api-client';

interface AuthContextType {
  user: UserResponse | null;
  loading: boolean;
  login: (credentials: UserLoginInput) => Promise<void>;
  register: (data: UserRegisterInput) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const userData = await api.users.getMe();
      setUser(userData);
    } catch (err) {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (credentials: UserLoginInput) => {
    setLoading(true);
    try {
      const res = await api.auth.login(credentials);
      setToken(res.access_token);
      setUser(res.user);
    } finally {
      setLoading(false);
    }
  };

  const register = async (data: UserRegisterInput) => {
    setLoading(true);
    try {
      const res = await api.auth.register(data);
      setToken(res.access_token);
      setUser(res.user);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

