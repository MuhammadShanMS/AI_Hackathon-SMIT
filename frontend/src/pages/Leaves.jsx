import React, { useState, useEffect } from 'react';
import { leaveService, orgService, aiService, getErrorMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  CalendarDays,
  Plus,
  Sparkles,
  CheckCircle,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Trash2,
  Clock,
  Send,
  X,
} from 'lucide-react';

export const Leaves = () => {
  const { role } = useAuth();
  const isHR = role === 'HR';

  const [balances, setBalances] = useState([]);
  const [leaves, setLeaves] = useState([]);
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState(null);

  // Apply Leave Modal
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [applyForm, setApplyForm] = useState({
    leave_type_id: '',
    start_date: '',
    end_date: '',
    reason: '',
  });

  // Smart Leave NLP input
  const [smartPrompt, setSmartPrompt] = useState('');
  const [smartLoading, setSmartLoading] = useState(false);

  // HR Review
  const [reviewModal, setReviewModal] = useState(null);
  const [reviewComment, setReviewComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      const [bRes, lRes, ltRes] = await Promise.all([
        leaveService.getBalances().catch(() => ({ data: [] })),
        leaveService.list().catch(() => ({ data: [] })),
        orgService.getLeaveTypes().catch(() => ({ data: [] })),
      ]);
      setBalances(bRes.data || []);
      setLeaves(lRes.data || []);
      setLeaveTypes(ltRes.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await leaveService.apply({
        leave_type_id: parseInt(applyForm.leave_type_id),
        start_date: applyForm.start_date,
        end_date: applyForm.end_date,
        reason: applyForm.reason,
      });
      setShowApplyModal(false);
      setApplyForm({ leave_type_id: '', start_date: '', end_date: '', reason: '' });
      setFeedback({ type: 'success', text: 'Leave application submitted successfully!' });
      fetchInitialData();
    } catch (err) {
      setFeedback({
        type: 'danger',
        text: getErrorMessage(err),
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async (id) => {
    if (!window.confirm('Cancel this pending leave request?')) return;
    try {
      await leaveService.cancel(id);
      setFeedback({ type: 'success', text: 'Leave request cancelled.' });
      fetchInitialData();
    } catch (err) {
      setFeedback({
        type: 'danger',
        text: getErrorMessage(err),
      });
    }
  };

  const handleReview = async (status) => {
    if (!reviewModal) return;
    try {
      setSubmitting(true);
      await leaveService.review(reviewModal.id, {
        status,
        comment: reviewComment || undefined,
      });
      setReviewModal(null);
      setReviewComment('');
      setFeedback({ type: 'success', text: `Leave application ${status.toLowerCase()}.` });
      fetchInitialData();
    } catch (err) {
      setFeedback({
        type: 'danger',
        text: getErrorMessage(err),
      });
    } finally {
      setSubmitting(false);
    }
  };

  // Smart Leave parsing
  const handleSmartLeaveParse = async (e) => {
    e.preventDefault();
    if (!smartPrompt.trim()) return;
    try {
      setSmartLoading(true);
      const { data } = await aiService.smartLeave(smartPrompt.trim());
      // data matches { type, start, end, reason }
      const matchedType = leaveTypes.find(
        (lt) => lt.name.toLowerCase() === (data.type || '').toLowerCase()
      );
      setApplyForm({
        leave_type_id: matchedType ? matchedType.id : (leaveTypes[0]?.id || ''),
        start_date: data.start || '',
        end_date: data.end || '',
        reason: data.reason || smartPrompt,
      });
      setShowApplyModal(true);
      setSmartPrompt('');
    } catch (err) {
      // If AI service is not yet enabled or errors, give guidance
      alert(getErrorMessage(err));
    } finally {
      setSmartLoading(false);
    }
  };

  return (
    <div>
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.75rem',
        }}
      >
        <div>
          <h2>Leave Management & Quota Accrual</h2>
          <p>Request time-off, track balance utilization, and manage manager approvals.</p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowApplyModal(true)}>
          <Plus size={16} /> Apply for Leave
        </button>
      </div>

      {feedback && (
        <div className={`alert alert-${feedback.type}`}>
          {feedback.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{feedback.text}</span>
        </div>
      )}

      {/* Smart Leave Assistant Box */}
      <div
        className="card"
        style={{
          marginBottom: '1.5rem',
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(6, 182, 212, 0.08))',
          borderColor: 'rgba(99, 102, 241, 0.3)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <Sparkles size={18} color="var(--accent-cyan)" />
          <h3 className="card-title" style={{ fontSize: '1rem' }}>Smart Leave Assistant (AI Natural Language)</h3>
        </div>
        <p style={{ fontSize: '0.85rem', marginBottom: '0.75rem' }}>
          Type your leave request naturally in English or Roman Urdu (e.g. <em>"Need sick leave tomorrow because of fever"</em> or <em>"Agly jummay ko annual leave chahye"</em>) and the AI will auto-populate your request.
        </p>
        <form onSubmit={handleSmartLeaveParse} style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            className="form-control"
            placeholder="e.g. Taking 2 days casual leave from Monday to Tuesday for family emergency"
            value={smartPrompt}
            onChange={(e) => setSmartPrompt(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" disabled={smartLoading}>
            {smartLoading ? <div className="spinner spinner-sm"></div> : <Send size={16} />}
          </button>
        </form>
      </div>

      {/* Quota Balances Grid */}
      <h3 style={{ marginBottom: '1rem' }}>Your Statutory Leave Balances</h3>
      <div className="metrics-grid">
        {balances.length === 0 ? (
          <div className="card" style={{ gridColumn: '1 / -1', padding: '1.25rem' }}>
            <p style={{ color: 'var(--text-muted)' }}>No personal leave quota assigned.</p>
          </div>
        ) : (
          balances.map((b) => (
            <div key={b.id} className="metric-card">
              <span className="metric-label">{b.leave_type_name}</span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem' }}>
                <span className="metric-value" style={{ color: 'var(--accent-cyan)' }}>
                  {b.balance_days}
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  / {b.yearly_quota} days left
                </span>
              </div>
              <span className="metric-sub">
                Used: {b.used_days} days • {b.is_paid ? 'Paid' : 'Unpaid'}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Leave Applications Table */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <div className="card-header">
          <h3 className="card-title">
            <Clock size={18} /> {isHR ? 'Workforce Leave Requests & Inbox' : 'Your Leave History'}
          </h3>
        </div>

        {loading ? (
          <div className="state-container">
            <div className="spinner"></div>
          </div>
        ) : leaves.length === 0 ? (
          <div className="state-container">
            <p>No leave requests found.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  {isHR && <th>Employee</th>}
                  <th>Leave Type</th>
                  <th>Date Range</th>
                  <th>Working Days</th>
                  <th>Reason</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {leaves.map((l) => (
                  <tr key={l.id}>
                    {isHR && (
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {l.employee_name || `Emp #${l.employee_id}`}
                      </td>
                    )}
                    <td>{l.leave_type_name}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {l.start_date} to {l.end_date}
                    </td>
                    <td style={{ fontWeight: 600 }}>{l.days_count}</td>
                    <td>{l.reason}</td>
                    <td>
                      <span
                        className={`badge ${
                          l.status === 'APPROVED'
                            ? 'badge-approved'
                            : l.status === 'REJECTED'
                            ? 'badge-rejected'
                            : 'badge-pending'
                        }`}
                      >
                        {l.status}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.35rem' }}>
                        {l.status === 'PENDING' && !isHR && (
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleCancel(l.id)}
                            title="Cancel Leave"
                          >
                            <Trash2 size={14} /> Cancel
                          </button>
                        )}
                        {isHR && l.status === 'PENDING' && (
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => setReviewModal(l)}
                          >
                            Review
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* APPLY LEAVE MODAL */}
      {showApplyModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h3>Submit Leave Request</h3>
              <button className="btn-icon" onClick={() => setShowApplyModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleApply}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Leave Type *</label>
                  <select
                    className="form-control"
                    value={applyForm.leave_type_id}
                    onChange={(e) => setApplyForm({ ...applyForm, leave_type_id: e.target.value })}
                    required
                  >
                    <option value="">Select Leave Type</option>
                    {leaveTypes.map((lt) => (
                      <option key={lt.id} value={lt.id}>
                        {lt.name} ({lt.yearly_quota} days/yr - {lt.is_paid ? 'Paid' : 'Unpaid'})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Start Date *</label>
                    <input
                      type="date"
                      className="form-control"
                      value={applyForm.start_date}
                      onChange={(e) => setApplyForm({ ...applyForm, start_date: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">End Date *</label>
                    <input
                      type="date"
                      className="form-control"
                      value={applyForm.end_date}
                      onChange={(e) => setApplyForm({ ...applyForm, end_date: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Reason *</label>
                  <textarea
                    className="form-control"
                    rows="3"
                    placeholder="Provide reason for time-off..."
                    value={applyForm.reason}
                    onChange={(e) => setApplyForm({ ...applyForm, reason: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowApplyModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Submitting...' : 'Apply for Leave'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* HR REVIEW LEAVE MODAL */}
      {reviewModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h3>Review Leave Request</h3>
              <button className="btn-icon" onClick={() => setReviewModal(null)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <p>
                <strong>Employee:</strong> {reviewModal.employee_name || reviewModal.employee_id}
              </p>
              <p>
                <strong>Leave Type:</strong> {reviewModal.leave_type_name}
              </p>
              <p>
                <strong>Duration:</strong> {reviewModal.start_date} to {reviewModal.end_date} (
                {reviewModal.days_count} working days)
              </p>
              <p>
                <strong>Reason:</strong> {reviewModal.reason}
              </p>

              <div className="form-group" style={{ marginTop: '1rem' }}>
                <label className="form-label">Review Comment (Optional)</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. Approved. Ensure handoff is done."
                  value={reviewComment}
                  onChange={(e) => setReviewComment(e.target.value)}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-danger"
                disabled={submitting}
                onClick={() => handleReview('REJECTED')}
              >
                Reject Request
              </button>
              <button
                type="button"
                className="btn btn-success"
                disabled={submitting}
                onClick={() => handleReview('APPROVED')}
              >
                Approve Leave
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
