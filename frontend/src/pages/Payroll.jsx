import React, { useState, useEffect } from 'react';
import { payrollService, getErrorMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  FileSpreadsheet,
  Download,
  Lock,
  Plus,
  CheckCircle2,
  AlertCircle,
  ShieldAlert,
  X,
} from 'lucide-react';

export const Payroll = () => {
  const { user, role } = useAuth();
  const isHR = role === 'HR';
  const isAdmin = role === 'ADMIN';
  const isEmployee = role === 'EMPLOYEE';

  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState(null);

  // New draft modal
  const [showDraftModal, setShowDraftModal] = useState(false);
  const now = new Date();
  const [draftMonth, setDraftMonth] = useState(now.getMonth() + 1);
  const [draftYear, setDraftYear] = useState(now.getFullYear());
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchRuns();
  }, []);

  const fetchRuns = async () => {
    try {
      setLoading(true);
      const { data } = await payrollService.getRuns();
      setRuns(data || []);
      if (data && data.length > 0) {
        loadRunDetails(data[0].id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadRunDetails = async (runId) => {
    try {
      const { data } = await payrollService.getRunDetails(runId);
      setSelectedRun(data);
    } catch (err) {
      console.error('Failed to load run details:', err);
    }
  };

  const handleCreateDraft = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      const { data } = await payrollService.createDraft(draftMonth, draftYear);
      setShowDraftModal(false);
      setFeedback({ type: 'success', text: `Draft payroll created for ${draftYear}-${draftMonth}.` });
      fetchRuns();
    } catch (err) {
      setFeedback({
        type: 'danger',
        text: getErrorMessage(err),
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleFinalize = async () => {
    if (!selectedRun) return;
    if (
      !window.confirm(
        `Are you sure you want to finalize payroll for ${selectedRun.year}-${selectedRun.month}? This action permanently locks the run and cannot be reversed.`
      )
    )
      return;

    try {
      setSubmitting(true);
      await payrollService.finalizeRun(selectedRun.id);
      setFeedback({ type: 'success', text: 'Payroll finalized and locked.' });
      loadRunDetails(selectedRun.id);
      fetchRuns();
    } catch (err) {
      setFeedback({
        type: 'danger',
        text: getErrorMessage(err),
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadPayslip = async (employeeId, month, year) => {
    try {
      const res = await payrollService.downloadPayslip(employeeId, month, year);
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `payslip_${employeeId}_${year}_${month}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert(getErrorMessage(err));
    }
  };

  return (
    <div>
      {/* Header */}
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
          <h2>Payroll & Compensation Management</h2>
          <p>Automated salary calculations, attendance deductions, statutory tax slabs, and payslips.</p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          {isHR && (
            <button className="btn btn-primary" onClick={() => setShowDraftModal(true)}>
              <Plus size={16} /> Generate Monthly Draft
            </button>
          )}
        </div>
      </div>

      {feedback && (
        <div className={`alert alert-${feedback.type}`}>
          {feedback.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{feedback.text}</span>
        </div>
      )}

      {loading ? (
        <div className="state-container">
          <div className="spinner"></div>
        </div>
      ) : runs.length === 0 ? (
        <div className="card state-container">
          <div className="empty-state-icon">
            <FileSpreadsheet size={32} />
          </div>
          <h3>No Payroll Runs Available</h3>
          <p>
            {isHR
              ? 'Click "Generate Monthly Draft" above to compute monthly compensation.'
              : 'Payroll has not yet been processed for your account.'}
          </p>
        </div>
      ) : (
        <div>
          {/* Payroll Run Selector Bar */}
          <div
            className="card"
            style={{
              marginBottom: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Select Period:</span>
              <select
                className="form-control"
                style={{ width: '180px' }}
                value={selectedRun?.id || ''}
                onChange={(e) => loadRunDetails(parseInt(e.target.value))}
              >
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.year}-{String(r.month).padStart(2, '0')} ({r.status})
                  </option>
                ))}
              </select>
            </div>

            {selectedRun && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span
                  className={`badge ${
                    selectedRun.status === 'FINALIZED' ? 'badge-locked' : 'badge-pending'
                  }`}
                >
                  {selectedRun.status === 'FINALIZED' && <Lock size={12} />}
                  {selectedRun.status}
                </span>

                {isAdmin && selectedRun.status === 'DRAFT' && (
                  <button
                    className="btn btn-success btn-sm"
                    onClick={handleFinalize}
                    disabled={submitting}
                  >
                    <Lock size={14} /> Finalize & Lock Run
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Run Details Table */}
          {selectedRun && (
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  Payroll Sheet: {selectedRun.year}-{String(selectedRun.month).padStart(2, '0')}
                </h3>
              </div>

              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Employee</th>
                      <th>Basic</th>
                      <th>Allowances</th>
                      <th>Gross</th>
                      <th>Absent / Unpaid</th>
                      <th>Income Tax</th>
                      <th>Net Payable</th>
                      <th>Payslip</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(selectedRun.items || []).map((item) => (
                      <tr key={item.id}>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                            {item.employee_name || `Emp #${item.employee_id}`}
                          </div>
                          <small style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                            {item.employee_code}
                          </small>
                        </td>
                        <td>${item.basic_salary?.toLocaleString()}</td>
                        <td>${item.allowances?.toLocaleString()}</td>
                        <td style={{ fontWeight: 600 }}>${item.gross_salary?.toLocaleString()}</td>
                        <td style={{ color: 'var(--status-danger)' }}>
                          -${(
                            (item.absent_deduction || 0) +
                            (item.unpaid_leave_deduction || 0) +
                            (item.half_day_deduction || 0)
                          ).toFixed(2)}
                        </td>
                        <td style={{ color: 'var(--accent-amber)' }}>
                          -${item.income_tax?.toFixed(2)}
                        </td>
                        <td style={{ fontWeight: 700, color: 'var(--accent-emerald)', fontSize: '1rem' }}>
                          ${item.net_salary?.toLocaleString()}
                        </td>
                        <td>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() =>
                              handleDownloadPayslip(
                                item.employee_id,
                                selectedRun.month,
                                selectedRun.year
                              )
                            }
                            title="Download PDF"
                          >
                            <Download size={14} /> PDF
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* DRAFT PAYROLL MODAL */}
      {showDraftModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h3>Generate Monthly Draft Payroll</h3>
              <button className="btn-icon" onClick={() => setShowDraftModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateDraft}>
              <div className="modal-body">
                <p style={{ fontSize: '0.85rem', marginBottom: '1rem' }}>
                  The engine will calculate gross pay, attendance deductions (absent days, unpaid leaves, half-days), joiner/leaver prorations, and progressive statutory annual tax slabs.
                </p>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Month</label>
                    <select
                      className="form-control"
                      value={draftMonth}
                      onChange={(e) => setDraftMonth(parseInt(e.target.value))}
                    >
                      {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                        <option key={m} value={m}>
                          {new Date(2000, m - 1).toLocaleString('default', { month: 'long' })}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Year</label>
                    <input
                      type="number"
                      className="form-control"
                      value={draftYear}
                      onChange={(e) => setDraftYear(parseInt(e.target.value) || 2026)}
                      required
                    />
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowDraftModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Calculating...' : 'Generate Draft'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
