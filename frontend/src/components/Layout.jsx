import React, { useState, useRef, useEffect } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { attendanceService, getErrorMessage } from '../services/api';
import { NotificationsDropdown } from './NotificationsDropdown';
import { AiChatDrawer } from './AiChatDrawer';
import { FaceCheckInModal } from './FaceCheckInModal';
import {
  LayoutDashboard,
  Users,
  Clock,
  CalendarDays,
  FileSpreadsheet,
  Megaphone,
  Settings,
  ShieldCheck,
  Building2,
  LogOut,
  Menu,
  X,
  Sparkles,
  LogIn,
  CheckCircle,
  ScanFace,
  ChevronDown,
  UserCheck,
} from 'lucide-react';

export const Layout = () => {
  const { user, role, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [checkInMsg, setCheckInMsg] = useState(null);
  const [checking, setChecking] = useState(false);
  const [showCheckInMenu, setShowCheckInMenu] = useState(false);
  const [showFaceModal, setShowFaceModal] = useState(false);
  const checkInMenuRef = useRef(null);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Close check-in menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (checkInMenuRef.current && !checkInMenuRef.current.contains(e.target)) {
        setShowCheckInMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleQuickCheckIn = async () => {
    try {
      setChecking(true);
      setShowCheckInMenu(false);
      await attendanceService.checkIn({ check_in_method: 'NORMAL' });
      setCheckInMsg({ type: 'success', text: 'Checked in! (Normal)' });
    } catch (err) {
      setCheckInMsg({ type: 'warning', text: getErrorMessage(err) });
    } finally {
      setChecking(false);
      setTimeout(() => setCheckInMsg(null), 4000);
    }
  };

  const handleFaceCheckInConfirm = async (geoData) => {
    await attendanceService.checkIn(geoData || { check_in_method: 'FACE_DETECTION', faces_detected: 1 });
    setCheckInMsg({ type: 'success', text: 'Checked in! (Face Detection)' });
    setTimeout(() => setCheckInMsg(null), 4000);
  };

  const handleQuickCheckOut = async () => {
    try {
      setChecking(true);
      await attendanceService.checkOut();
      setCheckInMsg({ type: 'success', text: 'Checked out successfully!' });
    } catch (err) {
      setCheckInMsg({ type: 'warning', text: getErrorMessage(err) });
    } finally {
      setChecking(false);
      setTimeout(() => setCheckInMsg(null), 4000);
    }
  };

  const navLinks = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard, roles: ['ADMIN', 'HR', 'EMPLOYEE'] },
    { to: '/employees', label: 'Employees', icon: Users, roles: ['ADMIN', 'HR'] },
    { to: '/attendance', label: 'Attendance', icon: Clock, roles: ['ADMIN', 'HR', 'EMPLOYEE'] },
    { to: '/leaves', label: 'Leaves', icon: CalendarDays, roles: ['ADMIN', 'HR', 'EMPLOYEE'] },
    { to: '/payroll', label: 'Payroll', icon: FileSpreadsheet, roles: ['ADMIN', 'HR', 'EMPLOYEE'] },
    { to: '/announcements', label: 'Announcements', icon: Megaphone, roles: ['ADMIN', 'HR', 'EMPLOYEE'] },
    { to: '/org-setup', label: 'Org Setup', icon: Building2, roles: ['ADMIN', 'HR'] },
    { to: '/settings', label: 'Company Settings', icon: Settings, roles: ['ADMIN'] },
    { to: '/audit-logs', label: 'Audit Logs', icon: ShieldCheck, roles: ['ADMIN'] },
  ];

  const visibleLinks = navLinks.filter((link) => link.roles.includes(role));

  return (
    <div className="app-container">
      {/* Mobile Backdrop */}
      {mobileMenuOpen && (
        <div className="sidebar-backdrop" onClick={() => setMobileMenuOpen(false)} />
      )}

      {/* Sidebar Navigation */}
      <aside className={`sidebar ${mobileMenuOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="logo-badge">
            <Sparkles size={20} />
          </div>
          <div className="logo-text">
            <span className="logo-title">HCM Lite</span>
            <span className="logo-subtitle">Intelligent HRMS</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {visibleLinks.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === '/'}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                onClick={() => setMobileMenuOpen(false)}
              >
                <Icon size={18} />
                <span>{link.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="user-snippet">
            <div className="user-avatar">
              {user?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="user-info">
              <span className="user-name">{user?.email}</span>
              <span className="user-role-badge">{role}</span>
            </div>
          </div>
          <button
            className="btn-icon"
            onClick={handleLogout}
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      {/* Main Workspace */}
      <div className="main-content">
        <header className="top-header">
          <div className="header-left">
            <button
              className="btn-icon"
              style={{ display: 'inline-flex' }}
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle Navigation"
            >
              {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <span className="header-title">Human Capital Management</span>
          </div>

          <div className="header-actions">
            {checkInMsg && (
              <span
                style={{
                  fontSize: '0.8rem',
                  padding: '0.25rem 0.65rem',
                  borderRadius: 'var(--radius-sm)',
                  background:
                    checkInMsg.type === 'success'
                      ? 'var(--status-success-bg)'
                      : 'var(--status-warning-bg)',
                  color:
                    checkInMsg.type === 'success' ? 'var(--status-success)' : 'var(--status-warning)',
                  border: '1px solid currentColor',
                }}
              >
                {checkInMsg.text}
              </span>
            )}

            {/* Quick check-in with dropdown */}
            <div style={{ display: 'flex', gap: '0.35rem', position: 'relative' }} ref={checkInMenuRef}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={handleQuickCheckIn}
                disabled={checking}
                title="Normal Check-in"
              >
                <LogIn size={14} /> In
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setShowCheckInMenu(!showCheckInMenu)}
                disabled={checking}
                title="More check-in options"
                style={{ padding: '0.25rem 0.35rem', minWidth: 'unset' }}
              >
                <ChevronDown size={12} />
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={handleQuickCheckOut}
                disabled={checking}
                title="Record Check-out"
              >
                <CheckCircle size={14} /> Out
              </button>

              {/* Dropdown menu */}
              {showCheckInMenu && (
                <div
                  style={{
                    position: 'absolute',
                    top: '100%',
                    right: 0,
                    marginTop: '0.5rem',
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-light)',
                    borderRadius: 'var(--radius-md)',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
                    minWidth: '220px',
                    zIndex: 1200,
                    overflow: 'hidden',
                  }}
                >
                  <button
                    onClick={handleQuickCheckIn}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem',
                      width: '100%',
                      padding: '0.85rem 1rem',
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-primary)',
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                      borderBottom: '1px solid var(--border-light)',
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(59,130,246,0.1)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <UserCheck size={18} color="#3b82f6" />
                    <div style={{ textAlign: 'left' }}>
                      <div style={{ fontWeight: 600 }}>Normal Check-In</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Quick one-click</div>
                    </div>
                  </button>
                  <button
                    onClick={() => {
                      setShowCheckInMenu(false);
                      setShowFaceModal(true);
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem',
                      width: '100%',
                      padding: '0.85rem 1rem',
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-primary)',
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(139,92,246,0.1)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <ScanFace size={18} color="#8b5cf6" />
                    <div style={{ textAlign: 'left' }}>
                      <div style={{ fontWeight: 600 }}>Face Detection</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>AI biometric</div>
                    </div>
                    <span
                      style={{
                        marginLeft: 'auto',
                        fontSize: '0.6rem',
                        fontWeight: 700,
                        color: '#8b5cf6',
                        background: 'rgba(139,92,246,0.15)',
                        padding: '0.15rem 0.4rem',
                        borderRadius: '4px',
                      }}
                    >
                      AI
                    </span>
                  </button>
                </div>
              )}
            </div>

            <NotificationsDropdown />
          </div>
        </header>

        <main className="page-container">
          <Outlet />
        </main>
      </div>

      {/* Face Detection Modal */}
      <FaceCheckInModal
        open={showFaceModal}
        onClose={() => setShowFaceModal(false)}
        onConfirm={handleFaceCheckInConfirm}
      />

      <AiChatDrawer />
    </div>
  );
};
