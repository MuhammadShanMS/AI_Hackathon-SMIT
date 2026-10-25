import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService, setupService } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('hcm_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('hcm_token'));
  const [loading, setLoading] = useState(true);
  const [isSetupDone, setIsSetupDone] = useState(true);

  // Check setup status and validate token on boot
  useEffect(() => {
    const initAuth = async () => {
      try {
        const { data: setupData } = await setupService.getStatus();
        setIsSetupDone(setupData.is_setup);
        if (!setupData.is_setup) {
          setLoading(false);
          return;
        }

        const savedToken = localStorage.getItem('hcm_token');
        if (savedToken) {
          const savedUser = localStorage.getItem('hcm_user');
          const parsedUser = savedUser ? JSON.parse(savedUser) : null;
          if (parsedUser?.must_change_password) {
            setUser(parsedUser);
          } else {
            try {
              const { data: userData } = await authService.getMe();
              setUser(userData);
              localStorage.setItem('hcm_user', JSON.stringify(userData));
            } catch (meErr) {
              if (parsedUser) {
                setUser(parsedUser);
              } else {
                throw meErr;
              }
            }
          }
        }
      } catch (err) {
        console.error('Auth initialization error:', err);
        localStorage.removeItem('hcm_token');
        localStorage.removeItem('hcm_user');
        setUser(null);
        setToken(null);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    const { data } = await authService.login(email, password);
    const accessToken = data.access_token;
    localStorage.setItem('hcm_token', accessToken);
    setToken(accessToken);

    let userData = {
      id: data.user_id,
      email,
      role: data.role,
      must_change_password: data.must_change_password,
      employee_id: data.employee_id,
    };

    if (!data.must_change_password) {
      try {
        const { data: meData } = await authService.getMe();
        userData = { ...userData, ...meData };
      } catch (err) {
        console.error('getMe error:', err);
      }
    }

    setUser(userData);
    localStorage.setItem('hcm_user', JSON.stringify(userData));
    return userData;
  };

  const logout = () => {
    localStorage.removeItem('hcm_token');
    localStorage.removeItem('hcm_user');
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const { data: userData } = await authService.getMe();
      setUser(userData);
      localStorage.setItem('hcm_user', JSON.stringify(userData));
      return userData;
    } catch (err) {
      console.error('Failed to refresh user:', err);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isSetupDone,
        setIsSetupDone,
        login,
        logout,
        refreshUser,
        role: user?.role,
        mustChangePassword: user?.must_change_password,
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
