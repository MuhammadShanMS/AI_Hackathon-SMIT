import React, { useState, useEffect } from 'react';
import { orgService, getErrorMessage } from '../services/api';
import { Settings as SettingsIcon, Save, CheckCircle2, AlertTriangle } from 'lucide-react';

export const Settings = () => {
  const [settings, setSettings] = useState({
    company_name: '',
    office_start_time: '09:00:00',
    grace_period_minutes: 15,
    half_day_hours: 4.0,
    weekend_days: 'Saturday, Sunday',
    office_latitude: 0.0,
    office_longitude: 0.0,
    office_radius_meters: 100,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const { data } = await orgService.getSettings();
      if (data) {
        setSettings(data);
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      setMessage(null);
      const { data } = await orgService.updateSettings(settings);
      setSettings(data);
      setMessage({ type: 'success', text: 'Company settings updated successfully.' });
    } catch (err) {
      setMessage({
        type: 'danger',
        text: getErrorMessage(err),
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="state-container">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: '1.75rem' }}>
        <h2>Company & System Settings</h2>
        <p>Configure core operational rules, attendance policies, and office geolocation boundaries.</p>
      </div>

      {message && (
        <div className={`alert alert-${message.type}`}>
          {message.type === 'success' ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
          <span>{message.text}</span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="card-header">
            <h3 className="card-title">
              <SettingsIcon size={20} /> Operational Parameters
            </h3>
          </div>

          <div className="form-group">
            <label className="form-label">Company / Organization Legal Name</label>
            <input
              type="text"
              className="form-control"
              value={settings.company_name}
              onChange={(e) => setSettings({ ...settings, company_name: e.target.value })}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Standard Office Start Time</label>
              <input
                type="text"
                className="form-control"
                placeholder="HH:MM:SS (e.g. 09:00:00)"
                value={settings.office_start_time}
                onChange={(e) => setSettings({ ...settings, office_start_time: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Grace Period (Minutes)</label>
              <input
                type="number"
                className="form-control"
                value={settings.grace_period_minutes}
                onChange={(e) =>
                  setSettings({ ...settings, grace_period_minutes: parseInt(e.target.value) || 0 })
                }
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Half-Day Threshold (Hours)</label>
              <input
                type="number"
                step="0.5"
                className="form-control"
                value={settings.half_day_hours}
                onChange={(e) =>
                  setSettings({ ...settings, half_day_hours: parseFloat(e.target.value) || 0 })
                }
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Weekend Days (Comma separated)</label>
            <input
              type="text"
              className="form-control"
              value={settings.weekend_days}
              onChange={(e) => setSettings({ ...settings, weekend_days: e.target.value })}
              required
            />
            <small style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: 4 }}>
              Typically: "Saturday, Sunday" or "Friday, Saturday"
            </small>
          </div>
        </div>

        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="card-header">
            <h3 className="card-title">Geofencing & Campus Coordinates</h3>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Office Latitude</label>
              <input
                type="number"
                step="0.000001"
                className="form-control"
                value={settings.office_latitude || 0}
                onChange={(e) =>
                  setSettings({ ...settings, office_latitude: parseFloat(e.target.value) || 0 })
                }
              />
            </div>

            <div className="form-group">
              <label className="form-label">Office Longitude</label>
              <input
                type="number"
                step="0.000001"
                className="form-control"
                value={settings.office_longitude || 0}
                onChange={(e) =>
                  setSettings({ ...settings, office_longitude: parseFloat(e.target.value) || 0 })
                }
              />
            </div>

            <div className="form-group">
              <label className="form-label">Check-in Radius (Meters)</label>
              <input
                type="number"
                className="form-control"
                value={settings.office_radius_meters || 100}
                onChange={(e) =>
                  setSettings({ ...settings, office_radius_meters: parseInt(e.target.value) || 0 })
                }
              />
            </div>
          </div>
        </div>

        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? (
            <>
              <div className="spinner spinner-sm"></div> Saving...
            </>
          ) : (
            <>
              <Save size={16} /> Save Settings
            </>
          )}
        </button>
      </form>
    </div>
  );
};
