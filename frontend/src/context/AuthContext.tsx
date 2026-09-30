import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole } from '../types';
import { api } from '../api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  role: UserRole | null;
  login: (email: string, pass: string) => Promise<void>;
  quickLoginAs: (role: UserRole) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('dss_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchCurrentUser = async () => {
    try {
      if (token) {
        const me = await api.getMe();
        setUser(me);
      }
    } catch (_) {
      logout();
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentUser();
  }, [token]);

  const login = async (email: string, pass: string) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', pass);
    
    const res = await api.login(formData);
    localStorage.setItem('dss_token', res.access_token);
    setToken(res.access_token);
    setUser({
      id: res.user_id,
      email: res.email,
      full_name: res.full_name,
      role: res.role as UserRole,
      is_active: true,
      created_at: new Date().toISOString()
    });
  };

  const quickLoginAs = async (targetRole: UserRole) => {
    const roleCredentials: Record<UserRole, { email: string; pass: string }> = {
      ADMIN: { email: 'admin@municipal.gov.in', pass: 'Admin@2026#DSS' },
      PLANNER: { email: 'planner@municipal.gov.in', pass: 'Planner@2026#DSS' },
      ANALYST: { email: 'analyst@municipal.gov.in', pass: 'Analyst@2026#DSS' },
      VIEWER: { email: 'viewer@municipal.gov.in', pass: 'Viewer@2026#DSS' }
    };
    const creds = roleCredentials[targetRole];
    await login(creds.email, creds.pass);
  };

  const logout = () => {
    localStorage.removeItem('dss_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role: user?.role || null,
        login,
        quickLoginAs,
        logout,
        isAuthenticated: !!token && !!user,
        isLoading
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
