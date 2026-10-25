import React, { useState, useEffect } from 'react';
import { attendanceService, getErrorMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { FaceCheckInModal } from '../components/FaceCheckInModal';
import {
  Clock,
  Calendar,
  ClipboardList,
  CheckCircle2,
  AlertCircle,
  LogIn,
  LogOut,
  Plus,
  X,
  FileCheck,
  ScanFace,
  UserCheck,
} from 'lucide-react';

export const Attendance = () => {
  const { role } = useAuth();
  const isHRorAdmin = role === 'HR' || role === 'ADMIN';

  const [activeTab, setActiveTab] = useState('calendar');
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Check-in method chooser
  const [showCheckInChooser, setShowCheckInChooser] = useState(false);
  const [showFaceModal, setShowFaceModal] = useState(false);

  // Calendar states
  const now = new Date();
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [calendarData, setCalendarData] = useState(null);

  // Daily Board states
  const [boardDate, setBoardDate] = useState(now.toISOString().split('T')[0]);
  const [boardData, setBoardData] = useState([]);

  // Corrections states
  const [corrections, setCorrections] = useState([]);
  const [showCorrectionModal, setShowCorrectionModal] = useState(false);
  const [correctionForm, setCorrectionForm] = useState({
    date: now.toISOString().split('T')[0],
    requested_check_in: '09:00:00',
    requested_check_out: '18:00:00',
    reason: '',
  });
  const [reviewModal, setReviewModal] = useState(null);
  const [reviewComment, setReviewComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (activeTab === 'calendar') {
      fetchCalendar();
    } else if (activeTab === 'daily-board') {
      fetchDailyBoard();
    } else if (activeTab === 'corrections') {
      fetchCorrections();
    }
  }, [activeTab, month, year, boardDate]);

  const fetchCalendar = async () => {
    try {
      setLoading(true);
      const { data } = await attendanceService.getCalendar({ month, year });
      setCalendarData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchDailyBoard = async () => {
    try {
      setLoading(true);
      const { data } = await attendanceService.getDailyBoard(boardDate);
      setBoardData(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchCorrections = async () => {
    try {
      setLoading(true);
      const { data } = await attendanceService.listCorrections();
      setCorrections(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleNormalCheckIn = async () => {
    try {
      setSubmitting(true);
      setShowCheckInChooser(false);
      await attendanceService.checkIn({ check_in_method: 'NORMAL' });
      setFeedback({ type: 'success', text: '✅ Checked in successfully! (Normal)' });
      if (activeTab === 'calendar') fetchCalendar();
      if (activeTab === 'daily-board') fetchDailyBoard();
    } catch (err) {
      setFeedback({
        type: 'warning',
        text: getErrorMessage(err),
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleFaceCheckInConfirm = async (geoData) => {
    // This is called by FaceCheckInModal when a face is successfully detected
    await attendanceService.checkIn(geoData || { check_in_method: 'FACE_DETECTION', faces_detected: 1 });
    setFeedback({ type: 'success', text: '✅ Checked in successfully via Face Detection!' });
    if (activeTab === 'calendar') fetchCalendar();
    if (activeTab === 'daily-board') fetchDailyBoard();
  };

  const handleCheckOut = async () => {
    try {
      setSubmitting(true);
      await attendanceService.checkOut();
      setFeedback({ type: 'success', text: 'Checked out successfully!' });
      if (activeTab === 'calendar') fetchCalendar();
      if (activeTab === 'daily-board') fetchDailyBoard();
    } catch (err) {
      setFeedback({
        type: 'warning',
        text: getErrorMessage(err),
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleRequestCorrection = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await attendanceService.requestCorrection(correctionForm);
      setShowCorrectionModal(false);
      setCorrectionForm({
        date: now.toISOString().split('T')[0],
        requested_check_in: '09:00:00',
        requested_check_out: '18:00:00',
        reason: '',
      });
      setFeedback({ type: 'success', text: 'Correction request submitted for review.' });
      fetchCorrections();
    } catch (err) {
      setFeedback({
        type: 'danger',
        text: getErrorMessage(err),
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleReviewCorrection = async (status) => {
    if (!reviewModal) return;
    try {
      setSubmitting(true);
      await attendanceService.reviewCorrection(reviewModal.id, {
        status,
        comment: reviewComment || undefined,
      });
      setReviewModal(null);
      setReviewComment('');
      setFeedback({ type: 'success', text: `Correction ${status.toLowerCase()} successfully.` });
      fetchCorrections();
    } catch (err) {
      setFeedback({
        type: 'danger',
        text: getErrorMessage(err),
      });
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'PRESENT':
        return 'badge-present';
      case 'LATE':
        return 'badge-late';
      case 'HALF_DAY':
        return 'badge-half-day';
      case 'ABSENT':
        return 'badge-absent';
      case 'ON_LEAVE':
        return 'badge-leave';
      case 'MISSING_CHECKOUT':
        return 'badge-missing';
      case 'WEEKEND':
      case 'HOLIDAY':
        return 'badge-neutral';
      default:
        return 'badge-neutral';
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
          <h2>Attendance & Time Tracking</h2>
          <p>Real-time check-in, dynamic calendar, daily floor board, and attendance corrections.</p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            className="btn btn-primary"
            onClick={() => setShowCheckInChooser(true)}
            disabled={submitting}
          >
            <LogIn size={16} /> Check In
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleCheckOut}
            disabled={submitting}
          >
            <LogOut size={16} /> Check Out
          </button>
        </div>
      </div>

      {/* Check-In Method Chooser Modal */}
      {showCheckInChooser && (
        <div className="modal-backdrop" style={{ zIndex: 1050 }}>
          <div className="modal-dialog" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <h3>Choose Check-In Method</h3>
              <button className="btn-icon" onClick={() => setShowCheckInChooser(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body" style={{ padding: '1.5rem' }}>
              <p style={{ color: 'var(--text-muted)', marginBottom: '1.25rem', fontSize: '0.9rem' }}>
                Select how you'd like to record your attendance today:
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {/* Normal Check-In */}
                <button
                  onClick={handleNormalCheckIn}
                  disabled={submitting}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    padding: '1.25rem',
                    background: 'rgba(59, 130, 246, 0.08)',
                    border: '1.5px solid rgba(59, 130, 246, 0.25)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    textAlign: 'left',
                    color: 'var(--text-primary)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(59, 130, 246, 0.15)';
                    e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(59, 130, 246, 0.08)';
                    e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.25)';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                >
                  <div
                    style={{
                      width: '52px',
                      height: '52px',
                      borderRadius: '14px',
                      background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <UserCheck size={24} color="#fff" />
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: '0.25rem' }}>
                      Normal Check-In
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Quick one-click attendance. Fast and simple.
                    </div>
                  </div>
                </button>

                {/* Face Detection Check-In */}
                <button
                  onClick={() => {
                    setShowCheckInChooser(false);
                    setShowFaceModal(true);
                  }}
                  disabled={submitting}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    padding: '1.25rem',
                    background: 'rgba(139, 92, 246, 0.08)',
                    border: '1.5px solid rgba(139, 92, 246, 0.25)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    textAlign: 'left',
                    color: 'var(--text-primary)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(139, 92, 246, 0.15)';
                    e.currentTarget.style.borderColor = 'rgba(139, 92, 246, 0.5)';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(139, 92, 246, 0.08)';
                    e.currentTarget.style.borderColor = 'rgba(139, 92, 246, 0.25)';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                >
                  <div
                    style={{
                      width: '52px',
                      height: '52px',
                      borderRadius: '14px',
                      background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <ScanFace size={24} color="#fff" />
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: '0.25rem' }}>
                      Face Detection Check-In
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      AI-powered biometric verification using your camera.
                    </div>
                  </div>
                  <span
                    style={{
                      marginLeft: 'auto',
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      color: '#8b5cf6',
                      background: 'rgba(139, 92, 246, 0.15)',
                      padding: '0.2rem 0.5rem',
                      borderRadius: '6px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px',
                      flexShrink: 0,
                    }}
                  >
                    AI
                  </span>
                </button>
              </div>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowCheckInChooser(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Face Detection Modal */}
      <FaceCheckInModal
        open={showFaceModal}
        onClose={() => setShowFaceModal(false)}
        onConfirm={handleFaceCheckInConfirm}
      />

      {feedback && (
        <div className={`alert alert-${feedback.type}`}>
          {feedback.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{feedback.text}</span>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <button
          className={`btn ${activeTab === 'calendar' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('calendar')}
        >
          <Calendar size={16} /> Monthly Calendar
        </button>
        {isHRorAdmin && (
          <button
            className={`btn ${activeTab === 'daily-board' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('daily-board')}
          >
            <Clock size={16} /> Daily Floor Board
          </button>
        )}
        <button
          className={`btn ${activeTab === 'corrections' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('corrections')}
        >
          <ClipboardList size={16} /> Corrections & Approvals
        </button>
      </div>

      {/* CALENDAR TAB */}
      {activeTab === 'calendar' && (
        <div>
          <div
            className="card"
            style={{
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <h3 className="card-title">Attendance Schedule: {year}-{String(month).padStart(2, '0')}</h3>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <select
                className="form-control"
                value={month}
                onChange={(e) => setMonth(parseInt(e.target.value))}
                style={{ width: '130px' }}
              >
                {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                  <option key={m} value={m}>
                    {new Date(2000, m - 1).toLocaleString('default', { month: 'long' })}
                  </option>
                ))}
              </select>
              <input
                type="number"
                className="form-control"
                value={year}
                onChange={(e) => setYear(parseInt(e.target.value) || 2026)}
                style={{ width: '100px' }}
              />
            </div>
          </div>

          {loading ? (
            <div className="state-container">
              <div className="spinner"></div>
            </div>
          ) : !calendarData ? (
            <div className="state-container">
              <p>No attendance data loaded.</p>
            </div>
          ) : (
            <div>
              {/* Summary KPIs */}
              <div className="metrics-grid">
                <div className="metric-card">
                  <span className="metric-label">Present Days</span>
                  <span className="metric-value" style={{ color: 'var(--status-success)' }}>
                    {calendarData.summary?.present || 0}
                  </span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Late Arrivals</span>
                  <span className="metric-value" style={{ color: 'var(--accent-amber)' }}>
                    {calendarData.summary?.late || 0}
                  </span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Half Days</span>
                  <span className="metric-value" style={{ color: 'var(--accent-purple)' }}>
                    {calendarData.summary?.half_day || 0}
                  </span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Calculated Absent</span>
                  <span className="metric-value" style={{ color: 'var(--status-danger)' }}>
                    {calendarData.summary?.absent || 0}
                  </span>
                </div>
              </div>

              {/* Calendar Grid */}
              <div className="card">
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))',
                    gap: '0.75rem',
                  }}
                >
                  {Object.entries(calendarData.days || {}).map(([dayKey, dayInfo]) => {
                    const status = typeof dayInfo === 'string' ? dayInfo : dayInfo.status;
                    return (
                      <div
                        key={dayKey}
                        style={{
                          background: 'rgba(255, 255, 255, 0.03)',
                          border: '1px solid var(--border-light)',
                          borderRadius: 'var(--radius-sm)',
                          padding: '0.75rem',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.35rem',
                        }}
                      >
                        <span
                          style={{
                            fontSize: '0.8rem',
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--text-muted)',
                          }}
                        >
                          {dayKey}
                        </span>
                        <span className={`badge ${getStatusBadgeClass(status)}`}>{status}</span>
                        {dayInfo?.check_in && (
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            In: {dayInfo.check_in.substring(11, 16)}
                          </span>
                        )}
                        {dayInfo?.check_out && (
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            Out: {dayInfo.check_out.substring(11, 16)}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* DAILY BOARD TAB */}
      {activeTab === 'daily-board' && isHRorAdmin && (
        <div>
          <div
            className="card"
            style={{
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <h3 className="card-title">Daily Floor Board for Date:</h3>
            <input
              type="date"
              className="form-control"
              style={{ width: '180px' }}
              value={boardDate}
              onChange={(e) => setBoardDate(e.target.value)}
            />
          </div>

          <div className="card">
            {loading ? (
              <div className="state-container">
                <div className="spinner"></div>
              </div>
            ) : boardData.length === 0 ? (
              <div className="state-container">
                <p>No records found for {boardDate}.</p>
              </div>
            ) : (
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Employee</th>
                      <th>Department</th>
                      <th>Status</th>
                      <th>Check In</th>
                      <th>Check Out</th>
                      <th>Hours</th>
                    </tr>
                  </thead>
                  <tbody>
                    {boardData.map((row, idx) => (
                      <tr key={idx}>
                        <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {row.employee_name} ({row.employee_code})
                        </td>
                        <td>{row.department_name}</td>
                        <td>
                          <span className={`badge ${getStatusBadgeClass(row.status)}`}>
                            {row.status}
                          </span>
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>
                          {row.check_in ? row.check_in.substring(11, 19) : '-'}
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>
                          {row.check_out ? row.check_out.substring(11, 19) : '-'}
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>
                          {row.hours_worked !== null && row.hours_worked !== undefined
                            ? `${row.hours_worked.toFixed(1)}h`
                            : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* CORRECTIONS TAB */}
      {activeTab === 'corrections' && (
        <div>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1.25rem',
            }}
          >
            <h3 className="card-title">Attendance Correction Requests</h3>
            <button className="btn btn-primary" onClick={() => setShowCorrectionModal(true)}>
              <Plus size={16} /> Request Correction
            </button>
          </div>

          <div className="card">
            {loading ? (
              <div className="state-container">
                <div className="spinner"></div>
              </div>
            ) : corrections.length === 0 ? (
              <div className="state-container">
                <p>No correction requests found.</p>
              </div>
            ) : (
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Employee</th>
                      <th>Requested In</th>
                      <th>Requested Out</th>
                      <th>Reason</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {corrections.map((c) => (
                      <tr key={c.id}>
                        <td>{c.date}</td>
                        <td style={{ fontWeight: 600 }}>{c.employee_name || `Emp #${c.employee_id}`}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{c.requested_check_in}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{c.requested_check_out}</td>
                        <td>{c.reason}</td>
                        <td>
                          <span
                            className={`badge ${
                              c.status === 'APPROVED'
                                ? 'badge-approved'
                                : c.status === 'REJECTED'
                                ? 'badge-rejected'
                                : 'badge-pending'
                            }`}
                          >
                            {c.status}
                          </span>
                        </td>
                        <td>
                          {isHRorAdmin && c.status === 'PENDING' && (
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => setReviewModal(c)}
                            >
                              <FileCheck size={14} /> Review
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* REQUEST CORRECTION MODAL */}
      {showCorrectionModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h3>Request Attendance Correction</h3>
              <button className="btn-icon" onClick={() => setShowCorrectionModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleRequestCorrection}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Date of Attendance *</label>
                  <input
                    type="date"
                    className="form-control"
                    value={correctionForm.date}
                    onChange={(e) =>
                      setCorrectionForm({ ...correctionForm, date: e.target.value })
                    }
                    required
                  />
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Requested Check-In (HH:MM:SS) *</label>
                    <input
                      type="text"
                      className="form-control"
                      value={correctionForm.requested_check_in}
                      onChange={(e) =>
                        setCorrectionForm({ ...correctionForm, requested_check_in: e.target.value })
                      }
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Requested Check-Out (HH:MM:SS) *</label>
                    <input
                      type="text"
                      className="form-control"
                      value={correctionForm.requested_check_out}
                      onChange={(e) =>
                        setCorrectionForm({ ...correctionForm, requested_check_out: e.target.value })
                      }
                      required
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Explanation / Reason *</label>
                  <textarea
                    className="form-control"
                    rows="3"
                    placeholder="Provide justification for adjustment..."
                    value={correctionForm.reason}
                    onChange={(e) =>
                      setCorrectionForm({ ...correctionForm, reason: e.target.value })
                    }
                    required
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowCorrectionModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  Submit Request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* REVIEW CORRECTION MODAL */}
      {reviewModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h3>Review Correction Request</h3>
              <button className="btn-icon" onClick={() => setReviewModal(null)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <p>
                <strong>Employee:</strong> {reviewModal.employee_name || reviewModal.employee_id}
              </p>
              <p>
                <strong>Date:</strong> {reviewModal.date}
              </p>
              <p>
                <strong>Requested Times:</strong> {reviewModal.requested_check_in} to{' '}
                {reviewModal.requested_check_out}
              </p>
              <p>
                <strong>Reason:</strong> {reviewModal.reason}
              </p>

              <div className="form-group" style={{ marginTop: '1rem' }}>
                <label className="form-label">Review Comment (Optional)</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. Approved per biometric verification"
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
                onClick={() => handleReviewCorrection('REJECTED')}
              >
                Reject Request
              </button>
              <button
                type="button"
                className="btn btn-success"
                disabled={submitting}
                onClick={() => handleReviewCorrection('APPROVED')}
              >
                Approve & Update Attendance
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
