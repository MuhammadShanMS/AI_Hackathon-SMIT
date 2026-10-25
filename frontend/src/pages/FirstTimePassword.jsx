import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authService, getErrorMessage } from '../services/api';
import { KeyRound, ShieldAlert, ArrowRight, CheckCircle2 } from 'lucide-react';

export const FirstTimePassword = () => {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    try {
      setLoading(true);
      await authService.changePassword(oldPassword, newPassword);
      await refreshUser();
      navigate('/');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem',
        background: 'radial-gradient(ellipse at 50% 20%, #171d3d 0%, #0b0f19 80%)',
      }}
    >
      <div
        className="card"
        style={{
          maxWidth: '460px',
          width: '100%',
          padding: '2.5rem 2rem',
          boxShadow: 'var(--shadow-glow), var(--shadow-lg)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
          <div
            className="logo-badge"
            style={{
              width: '48px',
              height: '48px',
              margin: '0 auto 1rem',
              background: 'linear-gradient(135deg, #f59e0b, #ef4444)',
            }}
          >
            <ShieldAlert size={24} />
          </div>
          <h1>Security Requirement</h1>
          <p style={{ marginTop: '0.35rem' }}>
            You are logging in with a temporary password. You must change your password before proceeding.
          </p>
        </div>

        {error && <div className="alert alert-danger">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Temporary / Current Password</label>
            <input
              type="password"
              className="form-control"
              placeholder="Enter temporary password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">New Secure Password</label>
            <input
              type="password"
              className="form-control"
              placeholder="Min 8 chars, 1 uppercase, 1 digit, 1 special"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Confirm New Password</label>
            <input
              type="password"
              className="form-control"
              placeholder="Confirm new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '1rem' }}
            disabled={loading}
          >
            {loading ? (
              <>
                <div className="spinner spinner-sm"></div> Updating...
              </>
            ) : (
              <>
                Update Password & Continue <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
