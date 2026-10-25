import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { ErrorBoundary } from './components/ErrorBoundary';

// Pages
import { Setup } from './pages/Setup';
import { Login } from './pages/Login';
import { FirstTimePassword } from './pages/FirstTimePassword';
import { Dashboard } from './pages/Dashboard';
import { Employees } from './pages/Employees';
import { Attendance } from './pages/Attendance';
import { Leaves } from './pages/Leaves';
import { Payroll } from './pages/Payroll';
import { Announcements } from './pages/Announcements';
import { OrgSetup } from './pages/OrgSetup';
import { Settings } from './pages/Settings';
import { AuditLogs } from './pages/AuditLogs';

export function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public / Bootstrap Routes */}
          <Route path="/setup" element={<Setup />} />
          <Route path="/login" element={<Login />} />

          {/* Forced rotation for must_change_password */}
          <Route
            path="/first-time-password"
            element={
              <ProtectedRoute>
                <FirstTimePassword />
              </ProtectedRoute>
            }
          />

          {/* Protected Application Workspace */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route
              path="employees"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'HR']}>
                  <Employees />
                </ProtectedRoute>
              }
            />
            <Route path="attendance" element={<Attendance />} />
            <Route path="leaves" element={<Leaves />} />
            <Route path="payroll" element={<Payroll />} />
            <Route path="announcements" element={<Announcements />} />
            <Route
              path="org-setup"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'HR']}>
                  <OrgSetup />
                </ProtectedRoute>
              }
            />
            <Route
              path="settings"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <Settings />
                </ProtectedRoute>
              }
            />
            <Route
              path="audit-logs"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <AuditLogs />
                </ProtectedRoute>
              }
            />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
