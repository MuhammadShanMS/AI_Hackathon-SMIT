import React, { useState, useEffect } from 'react';
import { commsService, getErrorMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Megaphone, Plus, Calendar, User, Send, CheckCircle2, AlertCircle } from 'lucide-react';

export const Announcements = () => {
  const { role } = useAuth();
  const canPost = role === 'ADMIN' || role === 'HR';

  const [announcements, setAnnouncements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    fetchAnnouncements();
  }, []);

  const fetchAnnouncements = async () => {
    try {
      setLoading(true);
      const { data } = await commsService.getAnnouncements();
      setAnnouncements(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handlePost = async (e) => {
    e.preventDefault();
    if (!title.trim() || !body.trim()) return;

    try {
      setSubmitting(true);
      const { data } = await commsService.createAnnouncement({
        title: title.trim(),
        body: body.trim(),
      });
      setAnnouncements([data, ...announcements]);
      setTitle('');
      setBody('');
      setFeedback({ type: 'success', text: 'Announcement published successfully to all staff.' });
    } catch (err) {
      setFeedback({
        type: 'danger',
        text: getErrorMessage(err),
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '1.75rem' }}>
        <h2>Company Announcements & Broadcasts</h2>
        <p>Organization-wide bulletins, policy updates, and executive announcements.</p>
      </div>

      {feedback && (
        <div className={`alert alert-${feedback.type}`}>
          {feedback.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{feedback.text}</span>
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: canPost ? '1fr 1.6fr' : '1fr',
          gap: '1.5rem',
        }}
      >
        {/* Post Form (HR & Admin) */}
        {canPost && (
          <div className="card" style={{ height: 'fit-content' }}>
            <div className="card-header">
              <h3 className="card-title">
                <Megaphone size={18} /> Broadcast New Notice
              </h3>
            </div>
            <form onSubmit={handlePost}>
              <div className="form-group">
                <label className="form-label">Title *</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. Annual Townhall & Hackathon Kickoff"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Message Content *</label>
                <textarea
                  className="form-control"
                  rows="5"
                  placeholder="Draft your announcement message here..."
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%' }}
                disabled={submitting}
              >
                {submitting ? 'Broadcasting...' : 'Publish Announcement'}
              </button>
            </form>
          </div>
        )}

        {/* Announcements List */}
        <div>
          {loading ? (
            <div className="state-container">
              <div className="spinner"></div>
            </div>
          ) : announcements.length === 0 ? (
            <div className="card state-container">
              <Megaphone size={32} color="var(--text-muted)" style={{ marginBottom: 12 }} />
              <h3>No announcements posted</h3>
              <p>Check back later for company updates.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {announcements.map((item) => (
                <div key={item.id} className="card">
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '0.75rem',
                      flexWrap: 'wrap',
                      gap: '0.5rem',
                    }}
                  >
                    <h3 style={{ fontSize: '1.15rem', color: 'var(--text-primary)' }}>
                      {item.title}
                    </h3>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        fontSize: '0.78rem',
                        color: 'var(--text-muted)',
                      }}
                    >
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Calendar size={13} />
                        {new Date(item.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{item.body}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
