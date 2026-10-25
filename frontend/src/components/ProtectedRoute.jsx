import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, token, loading, isSetupDone, mustChangePassword } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="state-container" style={{ minHeight: '100vh' }}>
        <div className="spinner"></div>
        <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>Loading HCM Lite...</p>
      </div>
    );
  }

  if (!isSetupDone && location.pathname !== '/setup') {
    return <Navigate to="/setup" replace />;
  }

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (mustChangePassword && location.pathname !== '/first-time-password') {
    return <Navigate to="/first-time-password" replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return children;
};
