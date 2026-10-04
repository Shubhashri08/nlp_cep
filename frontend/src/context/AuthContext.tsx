import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api, onUnauthorized, tokenStore } from '../api/client';
import type { PublicConfig, Role, TokenResponse, User } from '../types';

interface AuthState {
  user: User | null;
  config: PublicConfig | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  demoLogin: (role: Role) => Promise<void>;
  logout: () => void;
  hasRole: (...roles: Role[]) => boolean;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    onUnauthorized(() => setUser(null));
    api.config().then(setConfig).catch(() => setConfig(null));
    if (!tokenStore.get()) { setIsLoading(false); return; }
    api.me().then(setUser).catch(() => tokenStore.clear()).finally(() => setIsLoading(false));
  }, []);

  const accept = async (t: TokenResponse) => {
    tokenStore.set(t.access_token);
    setUser(await api.me());
  };
  const login = async (email: string, password: string) => accept(await api.login(email, password));
  const demoLogin = async (role: Role) => accept(await api.demoLogin(role));
  const hasRole = (...roles: Role[]) => !!user && (user.role === 'ADMIN' || roles.includes(user.role));

  return (
    <AuthContext.Provider value={{ user, config, isLoading, login, demoLogin, logout, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
};
