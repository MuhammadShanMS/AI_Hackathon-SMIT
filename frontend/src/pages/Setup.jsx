import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { setupService, getErrorMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Sparkles, Shield, Building, Lock, Mail, ArrowRight } from 'lucide-react';

export const Setup = () => {
  const navigate = useNavigate();
  const { setIsSetupDone } = useAuth();
  const [formData, setFormData] = useState({
    company_name: '',
    admin_email: '',
    admin_password: '',
    confirm_password: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // If setup already completed, go straight to login
  useEffect(() => {
    setupService.getStatus().then(({ data }) => {
      if (data.is_setup) navigate('/login', { replace: true });
    }).catch(() => {});
  }, [navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (formData.admin_password !== formData.confirm_password) {
      setError('Passwords do not match');
      return;
    }

    try {
      setLoading(true);
      await setupService.setup({
        company_name: formData.company_name,
        admin_email: formData.admin_email,
        admin_password: formData.admin_password,
      });
      setIsSetupDone(true);
      navigate('/login');
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
          maxWidth: '480px',
          width: '100%',
          padding: '2.25rem',
          boxShadow: 'var(--shadow-glow), var(--shadow-lg)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
          <div
            className="logo-badge"
            style={{ width: '48px', height: '48px', margin: '0 auto 1rem' }}
          >
            <Sparkles size={26} />
          </div>
          <h1>System Initialization</h1>
          <p style={{ marginTop: '0.35rem' }}>
            Welcome to HCM Lite. Configure your organization and primary root administrator account.
          </p>
        </div>

        {error && <div className="alert alert-danger">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">
              <Building size={14} style={{ display: 'inline', marginRight: 4 }} />
              Organization / Company Name <span className="required">*</span>
            </label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. Acme Innovations Corp"
              value={formData.company_name}
              onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">
              <Mail size={14} style={{ display: 'inline', marginRight: 4 }} />
              Admin Email Address <span className="required">*</span>
            </label>
            <input
              type="email"
              className="form-control"
              placeholder="admin@organization.com"
              value={formData.admin_email}
              onChange={(e) => setFormData({ ...formData, admin_email: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">
              <Lock size={14} style={{ display: 'inline', marginRight: 4 }} />
              Admin Password <span className="required">*</span>
            </label>
            <input
              type="password"
              className="form-control"
              placeholder="Min 8 chars, Aa1@..."
              value={formData.admin_password}
              onChange={(e) => setFormData({ ...formData, admin_password: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Confirm Password <span className="required">*</span></label>
            <input
              type="password"
              className="form-control"
              placeholder="Re-type password"
              value={formData.confirm_password}
              onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '0.75rem' }}
            disabled={loading}
          >
            {loading ? (
              <>
                <div className="spinner spinner-sm"></div> Initializing...
              </>
            ) : (
              <>
                Complete Setup <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
