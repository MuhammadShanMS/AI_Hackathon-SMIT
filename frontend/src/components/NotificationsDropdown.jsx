import React, { useState, useEffect } from 'react';
import { commsService } from '../services/api';
import { Bell, Check, CheckCheck, X } from 'lucide-react';

export const NotificationsDropdown = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const { data } = await commsService.getNotifications();
      setNotifications(data || []);
      const unread = (data || []).filter((n) => !n.is_read).length;
      setUnreadCount(unread);
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  const markAsRead = async (id, e) => {
    e?.stopPropagation();
    try {
      await commsService.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (err) {
      console.error('Failed to mark read:', err);
    }
  };

  const markAllRead = async () => {
    const unread = notifications.filter((n) => !n.is_read);
    for (const item of unread) {
      try {
        await commsService.markNotificationRead(item.id);
      } catch (e) {}
    }
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
  };

  return (
    <div style={{ position: 'relative' }}>
      <button
        className="btn-icon"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Notifications"
        style={{ position: 'relative' }}
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span
            style={{
              position: 'absolute',
              top: '-4px',
              right: '-4px',
              background: 'var(--status-danger)',
              color: '#fff',
              fontSize: '0.65rem',
              fontWeight: 700,
              width: '18px',
              height: '18px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 8px rgba(239, 68, 68, 0.6)',
            }}
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div
            style={{ position: 'fixed', inset: 0, zIndex: 60 }}
            onClick={() => setIsOpen(false)}
          />
          <div
            style={{
              position: 'absolute',
              right: 0,
              top: 'calc(100% + 8px)',
              width: '340px',
              maxWidth: '90vw',
              background: '#131b2e',
              border: '1px solid var(--border-medium)',
              borderRadius: 'var(--radius-md)',
              boxShadow: 'var(--shadow-lg)',
              zIndex: 70,
              overflow: 'hidden',
              animation: 'fadeIn 150ms ease-out',
            }}
          >
            <div
              style={{
                padding: '0.85rem 1rem',
                borderBottom: '1px solid var(--border-light)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                Notifications {unreadCount > 0 && `(${unreadCount})`}
              </div>
              {unreadCount > 0 && (
                <button
                  className="btn btn-ghost btn-sm"
                  style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}
                  onClick={markAllRead}
                >
                  <CheckCheck size={14} /> Mark all read
                </button>
              )}
            </div>

            <div style={{ maxHeight: '360px', overflowY: 'auto' }}>
              {loading && notifications.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center' }}>
                  <div className="spinner spinner-sm" style={{ margin: '0 auto' }}></div>
                </div>
              ) : notifications.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <p style={{ fontSize: '0.85rem' }}>No notifications yet</p>
                </div>
              ) : (
                notifications.map((item) => (
                  <div
                    key={item.id}
                    onClick={(e) => !item.is_read && markAsRead(item.id, e)}
                    style={{
                      padding: '0.75rem 1rem',
                      borderBottom: '1px solid var(--border-light)',
                      background: item.is_read ? 'transparent' : 'rgba(99, 102, 241, 0.08)',
                      cursor: item.is_read ? 'default' : 'pointer',
                      transition: 'background var(--transition-fast)',
                      display: 'flex',
                      alignItems: 'flex-start',
                      justifyContent: 'space-between',
                      gap: '0.5rem',
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontSize: '0.85rem',
                          color: item.is_read ? 'var(--text-secondary)' : 'var(--text-primary)',
                          fontWeight: item.is_read ? 400 : 600,
                        }}
                      >
                        {item.message}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                        {new Date(item.created_at).toLocaleString()}
                      </div>
                    </div>
                    {!item.is_read && (
                      <button
                        className="btn-icon"
                        style={{ padding: '0.25rem', width: '22px', height: '22px' }}
                        title="Mark as read"
                        onClick={(e) => markAsRead(item.id, e)}
                      >
                        <Check size={12} />
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
