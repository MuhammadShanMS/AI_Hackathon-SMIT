import React, { useState, useEffect } from 'react';
import { orgService, adminService, getErrorMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Building2,
  Award,
  CalendarHeart,
  CalendarCheck2,
  UserPlus,
  Plus,
  CheckCircle,
  AlertCircle,
  KeyRound,
  ShieldCheck,
  UserX,
  UserCheck,
} from 'lucide-react';

export const OrgSetup = () => {
  const { role } = useAuth();
  const isAdmin = role === 'ADMIN';

  const [activeTab, setActiveTab] = useState('departments');
  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState([]);
  const [designations, setDesignations] = useState([]);
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [holidays, setHolidays] = useState([]);
  const [users, setUsers] = useState([]);

  // Form states
  const [deptName, setDeptName] = useState('');
  const [desigTitle, setDesigTitle] = useState('');
  const [leaveTypeData, setLeaveTypeData] = useState({ name: '', yearly_quota: 10, is_paid: true });
  const [holidayData, setHolidayData] = useState({ date: '', name: '' });
  const [hrData, setHrData] = useState({ email: '', password: '' });
  const [resetModal, setResetModal] = useState({ open: false, user: null, tempPassword: '' });

  const [feedback, setFeedback] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const promises = [
        orgService.getDepartments(),
        orgService.getDesignations(),
        orgService.getLeaveTypes(),
        orgService.getHolidays(),
      ];
      if (isAdmin) {
        promises.push(adminService.getUsers());
      }
      const results = await Promise.all(promises);
      setDepartments(results[0].data || []);
      setDesignations(results[1].data || []);
      setLeaveTypes(results[2].data || []);
      setHolidays(results[3].data || []);
      if (isAdmin && results[4]) {
        setUsers(results[4].data || []);
      }
    } catch (err) {
      console.error('Failed to load org data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    if (!isAdmin) return;
    try {
      const { data } = await adminService.getUsers();
      setUsers(data || []);
    } catch (err) {
      console.error('Failed to fetch users:', err);
    }
  };

  const handleToggleUserStatus = async (user) => {
    try {
      setSubmitting(true);
      const newStatus = !user.is_active;
      await adminService.updateUserStatus(user.id, newStatus);
      setFeedback({
        type: 'success',
        text: `User ${user.email} ${newStatus ? 'activated' : 'deactivated'} successfully.`,
      });
      fetchUsers();
    } catch (err) {
      setFeedback({ type: 'danger', text: getErrorMessage(err) });
    } finally {
      setSubmitting(false);
    }
  };

  const handleResetPasswordSubmit = async (e) => {
    e.preventDefault();
    if (!resetModal.user || !resetModal.tempPassword) return;
    try {
      setSubmitting(true);
      await adminService.resetUserPassword(resetModal.user.id, resetModal.tempPassword);
      setFeedback({
        type: 'success',
        text: `Password for ${resetModal.user.email} reset successfully. User will be forced to change password on next sign-in.`,
      });
      setResetModal({ open: false, user: null, tempPassword: '' });
      fetchUsers();
    } catch (err) {
      setFeedback({ type: 'danger', text: getErrorMessage(err) });
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddDepartment = async (e) => {
    e.preventDefault();
    if (!deptName.trim()) return;
    try {
      setSubmitting(true);
      const { data } = await orgService.createDepartment({ name: deptName.trim() });
      setDepartments([...departments, data]);
      setDeptName('');
      setFeedback({ type: 'success', text: `Department "${data.name}" added successfully.` });
    } catch (err) {
      setFeedback({ type: 'danger', text: getErrorMessage(err) });
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddDesignation = async (e) => {
    e.preventDefault();
    if (!desigTitle.trim()) return;
    try {
      setSubmitting(true);
      const { data } = await orgService.createDesignation({
        name: desigTitle.trim(),
        title: desigTitle.trim(),
      });
      setDesignations([...designations, data]);
      setDesigTitle('');
      setFeedback({ type: 'success', text: `Designation "${data.title || data.name}" added successfully.` });
    } catch (err) {
      setFeedback({ type: 'danger', text: getErrorMessage(err) });
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddLeaveType = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      const { data } = await orgService.createLeaveType(leaveTypeData);
      setLeaveTypes([...leaveTypes, data]);
      setLeaveTypeData({ name: '', yearly_quota: 10, is_paid: true });
      setFeedback({ type: 'success', text: `Leave type "${data.name}" added successfully.` });
    } catch (err) {
      setFeedback({ type: 'danger', text: getErrorMessage(err) });
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddHoliday = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      const { data } = await orgService.createHoliday(holidayData);
      setHolidays([...holidays, data]);
      setHolidayData({ date: '', name: '' });
      setFeedback({ type: 'success', text: `Public holiday "${data.name}" registered.` });
    } catch (err) {
      setFeedback({ type: 'danger', text: getErrorMessage(err) });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateHr = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await orgService.createHrLogin(hrData.email, hrData.password);
      setHrData({ email: '', password: '' });
      setFeedback({ type: 'success', text: `HR login for ${hrData.email} provisioned successfully.` });
      fetchUsers();
    } catch (err) {
      setFeedback({ type: 'danger', text: getErrorMessage(err) });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '1.75rem' }}>
        <h2>Organizational Structure & Policies</h2>
        <p>Manage departments, job designations, statutory leave quotas, and holidays.</p>
      </div>

      {feedback && (
        <div className={`alert alert-${feedback.type}`}>
          {feedback.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
          <span>{feedback.text}</span>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <button
          className={`btn ${activeTab === 'departments' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('departments')}
        >
          <Building2 size={16} /> Departments ({departments.length})
        </button>
        <button
          className={`btn ${activeTab === 'designations' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('designations')}
        >
          <Award size={16} /> Designations ({designations.length})
        </button>
        <button
          className={`btn ${activeTab === 'leaves' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('leaves')}
        >
          <CalendarHeart size={16} /> Leave Types ({leaveTypes.length})
        </button>
        <button
          className={`btn ${activeTab === 'holidays' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('holidays')}
        >
          <CalendarCheck2 size={16} /> Holidays ({holidays.length})
        </button>
        {isAdmin && (
          <button
            className={`btn ${activeTab === 'create-hr' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('create-hr')}
          >
            <UserPlus size={16} /> User Logins & HR ({users.length})
          </button>
        )}
      </div>

      {loading ? (
        <div className="state-container">
          <div className="spinner"></div>
        </div>
      ) : (
        <div>
          {/* DEPARTMENTS TAB */}
          {activeTab === 'departments' && (
            <div style={{ display: 'grid', gridTemplateColumns: isAdmin ? '1fr 2fr' : '1fr', gap: '1.5rem' }}>
              {isAdmin && (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">Add Department</h3>
                  </div>
                  <form onSubmit={handleAddDepartment}>
                    <div className="form-group">
                      <label className="form-label">Department Name</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="e.g. Engineering, HR, Finance"
                        value={deptName}
                        onChange={(e) => setDeptName(e.target.value)}
                        required
                      />
                    </div>
                    <button type="submit" className="btn btn-primary" disabled={submitting}>
                      <Plus size={16} /> Add Department
                    </button>
                  </form>
                </div>
              )}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">Configured Departments</h3>
                </div>
                {departments.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)' }}>No departments defined yet.</p>
                ) : (
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Department Name</th>
                          <th>Created At</th>
                        </tr>
                      </thead>
                      <tbody>
                        {departments.map((d) => (
                          <tr key={d.id}>
                            <td>#{d.id}</td>
                            <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{d.name}</td>
                            <td>{new Date(d.created_at).toLocaleDateString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* DESIGNATIONS TAB */}
          {activeTab === 'designations' && (
            <div style={{ display: 'grid', gridTemplateColumns: isAdmin ? '1fr 2fr' : '1fr', gap: '1.5rem' }}>
              {isAdmin && (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">Add Designation</h3>
                  </div>
                  <form onSubmit={handleAddDesignation}>
                    <div className="form-group">
                      <label className="form-label">Job Title / Designation</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="e.g. Senior Software Engineer"
                        value={desigTitle}
                        onChange={(e) => setDesigTitle(e.target.value)}
                        required
                      />
                    </div>
                    <button type="submit" className="btn btn-primary" disabled={submitting}>
                      <Plus size={16} /> Add Designation
                    </button>
                  </form>
                </div>
              )}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">Configured Designations</h3>
                </div>
                {designations.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)' }}>No designations defined yet.</p>
                ) : (
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Title</th>
                          <th>Created At</th>
                        </tr>
                      </thead>
                      <tbody>
                        {designations.map((des) => (
                          <tr key={des.id}>
                            <td>#{des.id}</td>
                            <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{des.name || des.title}</td>
                            <td>{des.created_at ? new Date(des.created_at).toLocaleDateString() : '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* LEAVE TYPES TAB */}
          {activeTab === 'leaves' && (
            <div style={{ display: 'grid', gridTemplateColumns: isAdmin ? '1fr 2fr' : '1fr', gap: '1.5rem' }}>
              {isAdmin && (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">Add Leave Type</h3>
                  </div>
                  <form onSubmit={handleAddLeaveType}>
                    <div className="form-group">
                      <label className="form-label">Leave Type Name</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="e.g. Annual, Casual, Sick"
                        value={leaveTypeData.name}
                        onChange={(e) => setLeaveTypeData({ ...leaveTypeData, name: e.target.value })}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Yearly Quota (Days)</label>
                      <input
                        type="number"
                        className="form-control"
                        value={leaveTypeData.yearly_quota}
                        onChange={(e) =>
                          setLeaveTypeData({
                            ...leaveTypeData,
                            yearly_quota: parseInt(e.target.value) || 0,
                          })
                        }
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={leaveTypeData.is_paid}
                          onChange={(e) =>
                            setLeaveTypeData({ ...leaveTypeData, is_paid: e.target.checked })
                          }
                        />
                        <span>Is Paid Leave</span>
                      </label>
                    </div>
                    <button type="submit" className="btn btn-primary" disabled={submitting}>
                      <Plus size={16} /> Save Leave Type
                    </button>
                  </form>
                </div>
              )}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">Configured Leave Types</h3>
                </div>
                {leaveTypes.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)' }}>No leave types configured.</p>
                ) : (
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Name</th>
                          <th>Annual Quota</th>
                          <th>Type</th>
                        </tr>
                      </thead>
                      <tbody>
                        {leaveTypes.map((lt) => (
                          <tr key={lt.id}>
                            <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{lt.name}</td>
                            <td>{lt.yearly_quota} days</td>
                            <td>
                              <span className={`badge ${lt.is_paid ? 'badge-approved' : 'badge-rejected'}`}>
                                {lt.is_paid ? 'Paid' : 'Unpaid'}
                              </span>
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

          {/* PUBLIC HOLIDAYS TAB */}
          {activeTab === 'holidays' && (
            <div style={{ display: 'grid', gridTemplateColumns: isAdmin ? '1fr 2fr' : '1fr', gap: '1.5rem' }}>
              {isAdmin && (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">Register Public Holiday</h3>
                  </div>
                  <form onSubmit={handleAddHoliday}>
                    <div className="form-group">
                      <label className="form-label">Holiday Date</label>
                      <input
                        type="date"
                        className="form-control"
                        value={holidayData.date}
                        onChange={(e) => setHolidayData({ ...holidayData, date: e.target.value })}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Holiday Name</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="e.g. Independence Day"
                        value={holidayData.name}
                        onChange={(e) => setHolidayData({ ...holidayData, name: e.target.value })}
                        required
                      />
                    </div>
                    <button type="submit" className="btn btn-primary" disabled={submitting}>
                      <Plus size={16} /> Add Holiday
                    </button>
                  </form>
                </div>
              )}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">Configured Public Holidays</h3>
                </div>
                {holidays.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)' }}>No holidays registered.</p>
                ) : (
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Holiday Name</th>
                        </tr>
                      </thead>
                      <tbody>
                        {holidays.map((h) => (
                          <tr key={h.id}>
                            <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{h.date}</td>
                            <td>{h.name}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* USERS & HR LOGINS TAB (Functionality #05) */}
          {activeTab === 'create-hr' && isAdmin && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1.5rem', alignItems: 'start' }}>
              {/* Provision HR Card */}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">
                    <UserPlus size={20} /> Provision HR Personnel
                  </h3>
                </div>
                <p style={{ marginBottom: '1.25rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                  HR users manage workforce directories, attendance corrections, leave approvals, and payroll drafts.
                </p>
                <form onSubmit={handleCreateHr}>
                  <div className="form-group">
                    <label className="form-label">HR Email Address</label>
                    <input
                      type="email"
                      className="form-control"
                      placeholder="hr.officer@organization.com"
                      value={hrData.email}
                      onChange={(e) => setHrData({ ...hrData, email: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Temporary Initial Password</label>
                    <input
                      type="password"
                      className="form-control"
                      placeholder="Min 8 characters"
                      value={hrData.password}
                      onChange={(e) => setHrData({ ...hrData, password: e.target.value })}
                      required
                    />
                  </div>
                  <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={submitting}>
                    <UserPlus size={16} /> Create HR Login
                  </button>
                </form>
              </div>

              {/* System Users Table */}
              <div className="card">
                <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 className="card-title">
                    <ShieldCheck size={20} /> All Logins & Access Control ({users.length})
                  </h3>
                  <button className="btn btn-secondary btn-sm" onClick={fetchUsers} disabled={submitting}>
                    Refresh Logins
                  </button>
                </div>
                <p style={{ marginBottom: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                  Admin control: Deactivate access or issue temporary passwords forcing password rotation on next login.
                </p>
                <div className="table-responsive">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>User / Email</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Temp Pass</th>
                        <th style={{ textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.length === 0 ? (
                        <tr>
                          <td colSpan="5" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>
                            No users registered yet.
                          </td>
                        </tr>
                      ) : (
                        users.map((u) => (
                          <tr key={u.id}>
                            <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{u.email}</td>
                            <td>
                              <span
                                className={`badge ${
                                  u.role === 'ADMIN'
                                    ? 'badge-primary'
                                    : u.role === 'HR'
                                    ? 'badge-info'
                                    : 'badge-neutral'
                                }`}
                              >
                                {u.role}
                              </span>
                            </td>
                            <td>
                              <span className={`badge ${u.is_active ? 'badge-success' : 'badge-danger'}`}>
                                {u.is_active ? 'Active' : 'Deactivated'}
                              </span>
                            </td>
                            <td>
                              <span style={{ fontSize: '0.8rem', color: u.must_change_password ? 'var(--accent-amber)' : 'var(--text-muted)' }}>
                                {u.must_change_password ? 'Required' : 'No'}
                              </span>
                            </td>
                            <td style={{ textAlign: 'right' }}>
                              <div style={{ display: 'inline-flex', gap: '0.4rem', justifyContent: 'flex-end' }}>
                                <button
                                  className={`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-success'}`}
                                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                  onClick={() => handleToggleUserStatus(u)}
                                  disabled={submitting}
                                  title={u.is_active ? 'Deactivate user' : 'Activate user'}
                                >
                                  {u.is_active ? <UserX size={14} /> : <UserCheck size={14} />}
                                  {u.is_active ? ' Deactivate' : ' Activate'}
                                </button>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                  onClick={() => setResetModal({ open: true, user: u, tempPassword: '' })}
                                  disabled={submitting}
                                  title="Reset password"
                                >
                                  <KeyRound size={14} /> Reset Pass
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Reset Password Modal */}
          {resetModal.open && resetModal.user && (
            <div
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0,0,0,0.7)',
                backdropFilter: 'blur(4px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 9999,
                padding: '1rem',
              }}
            >
              <div className="card" style={{ maxWidth: '440px', width: '100%' }}>
                <div className="card-header">
                  <h3 className="card-title">
                    <KeyRound size={20} /> Reset User Password
                  </h3>
                </div>
                <p style={{ marginBottom: '1rem', fontSize: '0.875rem' }}>
                  Issue a temporary password for <strong>{resetModal.user.email}</strong>. The user will be required to change it on their next sign-in.
                </p>
                <form onSubmit={handleResetPasswordSubmit}>
                  <div className="form-group">
                    <label className="form-label">New Temporary Password</label>
                    <input
                      type="password"
                      className="form-control"
                      placeholder="Min 8 characters"
                      value={resetModal.tempPassword}
                      onChange={(e) => setResetModal({ ...resetModal, tempPassword: e.target.value })}
                      required
                      autoFocus
                    />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.25rem' }}>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setResetModal({ open: false, user: null, tempPassword: '' })}
                      disabled={submitting}
                    >
                      Cancel
                    </button>
                    <button type="submit" className="btn btn-primary" disabled={submitting || !resetModal.tempPassword}>
                      Confirm Reset
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
