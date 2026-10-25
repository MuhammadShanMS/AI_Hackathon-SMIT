import React, { useState, useEffect } from 'react';
import { employeeService, orgService, getErrorMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Users,
  UserPlus,
  Search,
  Filter,
  Download,
  Upload,
  Eye,
  Edit2,
  Copy,
  Check,
  X,
  AlertCircle,
  CheckCircle2,
  FileSpreadsheet,
} from 'lucide-react';

export const Employees = () => {
  const { user, role } = useAuth();
  const isHR = role === 'HR';
  const isAdmin = role === 'ADMIN';

  // Data states
  const [employees, setEmployees] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [search, setSearch] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);

  // Reference catalogs
  const [departments, setDepartments] = useState([]);
  const [designations, setDesignations] = useState([]);

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [tempPasswordModal, setTempPasswordModal] = useState(null);
  const [showCsvModal, setShowCsvModal] = useState(false);

  // Form states
  const [newEmp, setNewEmp] = useState({
    first_name: '',
    last_name: '',
    email: '',
    department_id: '',
    designation_id: '',
    basic_salary: '',
    allowances: '0',
    date_of_joining: new Date().toISOString().split('T')[0],
    joining_date: new Date().toISOString().split('T')[0],
    gender: 'Unspecified',
  });
  const [editSelf, setEditSelf] = useState({ phone: '', address: '' });
  const [copied, setCopied] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // CSV Import States
  const [csvFile, setCsvFile] = useState(null);
  const [csvDryRunResult, setCsvDryRunResult] = useState(null);
  const [csvImporting, setCsvImporting] = useState(false);

  useEffect(() => {
    fetchCatalogs();
  }, []);

  useEffect(() => {
    fetchEmployees();
  }, [page, departmentId, statusFilter]);

  const fetchCatalogs = async () => {
    try {
      const [deptRes, desigRes] = await Promise.all([
        orgService.getDepartments(),
        orgService.getDesignations(),
      ]);
      setDepartments(deptRes.data || []);
      setDesignations(desigRes.data || []);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchEmployees = async () => {
    try {
      setLoading(true);
      const params = {
        page,
        limit,
        search: search.trim() || undefined,
        department_id: departmentId || undefined,
        status: statusFilter || undefined,
      };
      const { data } = await employeeService.list(params);
      setEmployees(data.items || []);
      setTotal(data.total || 0);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchEmployees();
  };

  const handleCreateEmployee = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setErrorMsg(null);
      const payload = {
        ...newEmp,
        joining_date: newEmp.joining_date || newEmp.date_of_joining,
        date_of_joining: newEmp.joining_date || newEmp.date_of_joining,
        department_id: parseInt(newEmp.department_id),
        designation_id: parseInt(newEmp.designation_id),
        basic_salary: parseFloat(newEmp.basic_salary),
        allowances: parseFloat(newEmp.allowances || 0),
      };
      const { data } = await employeeService.create(payload);
      setShowAddModal(false);
      setTempPasswordModal({
        email: newEmp.email,
        password: data.temporary_password,
        name: `${newEmp.first_name} ${newEmp.last_name}`,
      });
      setNewEmp({
        first_name: '',
        last_name: '',
        email: '',
        department_id: '',
        designation_id: '',
        basic_salary: '',
        allowances: '0',
        date_of_joining: new Date().toISOString().split('T')[0],
        joining_date: new Date().toISOString().split('T')[0],
        gender: 'Unspecified',
      });
      fetchEmployees();
    } catch (err) {
      setErrorMsg(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const openProfile = async (empId) => {
    try {
      const { data } = await employeeService.get(empId);
      setSelectedEmployee(data);
      setEditSelf({ phone: data.phone || '', address: data.address || '' });
      setShowProfileModal(true);
    } catch (err) {
      alert(getErrorMessage(err));
    }
  };

  const handleUpdateSelf = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await employeeService.updateSelf(editSelf);
      if (selectedEmployee) {
        setSelectedEmployee({ ...selectedEmployee, ...editSelf });
      }
      alert('Profile contact details updated successfully');
    } catch (err) {
      alert(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleExportCsv = async () => {
    try {
      const response = await employeeService.exportCsv();
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `employees_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Failed to export CSV');
    }
  };

  const handleCsvDryRun = async () => {
    if (!csvFile) return;
    try {
      setCsvImporting(true);
      setCsvDryRunResult(null);
      const { data } = await employeeService.importCsv(csvFile, true);
      setCsvDryRunResult(data);
    } catch (err) {
      alert(getErrorMessage(err));
    } finally {
      setCsvImporting(false);
    }
  };

  const handleCsvFinalImport = async () => {
    if (!csvFile) return;
    try {
      setCsvImporting(true);
      const { data } = await employeeService.importCsv(csvFile, false);
      alert(`Import completed! Successfully imported ${data.success_count} employees.`);
      setShowCsvModal(false);
      setCsvFile(null);
      setCsvDryRunResult(null);
      fetchEmployees();
    } catch (err) {
      alert(getErrorMessage(err));
    } finally {
      setCsvImporting(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div>
      {/* Header bar */}
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
          <h2>Employee Directory & 360 Profiles</h2>
          <p>Search, manage workforce details, roles, salaries, and secure employee onboarding.</p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {isHR && (
            <>
              <button className="btn btn-secondary" onClick={() => setShowCsvModal(true)}>
                <Upload size={16} /> Import CSV
              </button>
              <button className="btn btn-secondary" onClick={handleExportCsv}>
                <Download size={16} /> Export CSV
              </button>
              <button
                className="btn btn-primary"
                onClick={() => {
                  fetchCatalogs();
                  setShowAddModal(true);
                }}
              >
                <UserPlus size={16} /> Register Employee
              </button>
            </>
          )}
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="card" style={{ marginBottom: '1.5rem', padding: '1rem 1.25rem' }}>
        <form
          onSubmit={handleSearchSubmit}
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr)) auto',
            gap: '0.75rem',
            alignItems: 'center',
          }}
        >
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              className="form-control"
              placeholder="Search by name, email, code..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div>
            <select
              className="form-control"
              value={departmentId}
              onChange={(e) => setDepartmentId(e.target.value)}
            >
              <option value="">All Departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <select
              className="form-control"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>
          </div>

          <button type="submit" className="btn btn-primary">
            <Search size={16} /> Filter
          </button>
        </form>
      </div>

      {/* Employee List Table */}
      <div className="card">
        {loading ? (
          <div className="state-container">
            <div className="spinner"></div>
          </div>
        ) : employees.length === 0 ? (
          <div className="state-container">
            <div className="empty-state-icon">
              <Users size={32} />
            </div>
            <h3>No employees found</h3>
            <p>Try adjusting your search criteria or register a new employee.</p>
          </div>
        ) : (
          <>
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Emp Code</th>
                    <th>Full Name</th>
                    <th>Department</th>
                    <th>Designation</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.map((emp) => (
                    <tr key={emp.id}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                        {emp.employee_code}
                      </td>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {emp.first_name} {emp.last_name}
                      </td>
                      <td>{emp.department?.name || emp.department_name || '-'}</td>
                      <td>{emp.designation?.title || emp.designation_title || '-'}</td>
                      <td>{emp.email}</td>
                      <td>
                        <span
                          className={`badge ${
                            emp.status === 'ACTIVE' ? 'badge-approved' : 'badge-rejected'
                          }`}
                        >
                          {emp.status}
                        </span>
                      </td>
                      <td>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => openProfile(emp.id)}
                        >
                          <Eye size={14} /> View 360
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginTop: '1.25rem',
                flexWrap: 'wrap',
                gap: '0.75rem',
              }}
            >
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Showing {employees.length} of {total} employees
              </span>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  className="btn btn-secondary btn-sm"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </button>
                <span
                  style={{
                    padding: '0.35rem 0.75rem',
                    fontSize: '0.85rem',
                    color: 'var(--text-primary)',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  Page {page}
                </span>
                <button
                  className="btn btn-secondary btn-sm"
                  disabled={page * limit >= total}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* REGISTER EMPLOYEE MODAL */}
      {showAddModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h3>Register New Employee</h3>
              <button className="btn-icon" onClick={() => setShowAddModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateEmployee}>
              <div className="modal-body">
                {errorMsg && <div className="alert alert-danger">{errorMsg}</div>}

                {(departments.length === 0 || designations.length === 0) && (
                  <div className="alert alert-warning" style={{ marginBottom: '1.25rem' }}>
                    <span>
                      <strong>Setup required:</strong> No {departments.length === 0 && designations.length === 0 ? 'departments or designations' : departments.length === 0 ? 'departments' : 'designations'} have been created yet. Please add them first in <a href="/org-setup" style={{ color: 'var(--primary)', fontWeight: 600, textDecoration: 'underline' }}>Org Setup</a>.
                    </span>
                  </div>
                )}

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">First Name *</label>
                    <input
                      type="text"
                      className="form-control"
                      value={newEmp.first_name}
                      onChange={(e) => setNewEmp({ ...newEmp, first_name: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Last Name *</label>
                    <input
                      type="text"
                      className="form-control"
                      value={newEmp.last_name}
                      onChange={(e) => setNewEmp({ ...newEmp, last_name: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Corporate Email Address *</label>
                  <input
                    type="email"
                    className="form-control"
                    value={newEmp.email}
                    onChange={(e) => setNewEmp({ ...newEmp, email: e.target.value })}
                    required
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Department *</label>
                    <select
                      className="form-control"
                      value={newEmp.department_id}
                      onChange={(e) => setNewEmp({ ...newEmp, department_id: e.target.value })}
                      required
                    >
                      <option value="">Select Department</option>
                      {departments.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Designation *</label>
                    <select
                      className="form-control"
                      value={newEmp.designation_id}
                      onChange={(e) => setNewEmp({ ...newEmp, designation_id: e.target.value })}
                      required
                    >
                      <option value="">Select Designation</option>
                      {designations.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name || d.title}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Basic Salary (Monthly) *</label>
                    <input
                      type="number"
                      className="form-control"
                      placeholder="e.g. 50000"
                      value={newEmp.basic_salary}
                      onChange={(e) => setNewEmp({ ...newEmp, basic_salary: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Allowances</label>
                    <input
                      type="number"
                      className="form-control"
                      value={newEmp.allowances}
                      onChange={(e) => setNewEmp({ ...newEmp, allowances: e.target.value })}
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Date of Joining *</label>
                    <input
                      type="date"
                      className="form-control"
                      value={newEmp.joining_date || newEmp.date_of_joining || ''}
                      onChange={(e) =>
                        setNewEmp({
                          ...newEmp,
                          date_of_joining: e.target.value,
                          joining_date: e.target.value,
                        })
                      }
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Gender</label>
                    <select
                      className="form-control"
                      value={newEmp.gender}
                      onChange={(e) => setNewEmp({ ...newEmp, gender: e.target.value })}
                    >
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                      <option value="Unspecified">Unspecified</option>
                    </select>
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowAddModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Registering...' : 'Register Employee'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TEMPORARY PASSWORD ONE-TIME POPUP */}
      {tempPasswordModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle2 color="var(--status-success)" /> Employee Created
              </h3>
            </div>
            <div className="modal-body">
              <p style={{ marginBottom: '1rem' }}>
                Employee <strong>{tempPasswordModal.name}</strong> has been registered. Share the
                temporary password below. <em>This password will never be shown again!</em>
              </p>

              <div
                style={{
                  background: 'rgba(0, 0, 0, 0.4)',
                  padding: '1rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-medium)',
                  marginBottom: '1rem',
                }}
              >
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Login Email:</div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
                  {tempPasswordModal.email}
                </div>

                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Temporary Password:</div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '1.25rem',
                    fontWeight: 700,
                    color: 'var(--accent-cyan)',
                  }}
                >
                  <span>{tempPasswordModal.password}</span>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => copyToClipboard(tempPasswordModal.password)}
                  >
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>

              <div className="alert alert-warning" style={{ fontSize: '0.8rem' }}>
                The user will be required to change this password on their initial login attempt.
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn btn-primary"
                onClick={() => setTempPasswordModal(null)}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* EMPLOYEE 360 MODAL */}
      {showProfileModal && selectedEmployee && (
        <div className="modal-backdrop">
          <div className="modal-dialog" style={{ maxWidth: '680px' }}>
            <div className="modal-header">
              <h3>
                Employee 360: {selectedEmployee.first_name} {selectedEmployee.last_name}
              </h3>
              <button className="btn-icon" onClick={() => setShowProfileModal(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '1rem',
                  marginBottom: '1.5rem',
                }}
              >
                <div>
                  <small style={{ color: 'var(--text-muted)' }}>Employee Code</small>
                  <p style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    {selectedEmployee.employee_code}
                  </p>
                </div>
                <div>
                  <small style={{ color: 'var(--text-muted)' }}>Department</small>
                  <p>{selectedEmployee.department?.name || selectedEmployee.department_name}</p>
                </div>
                <div>
                  <small style={{ color: 'var(--text-muted)' }}>Designation</small>
                  <p>{selectedEmployee.designation?.title || selectedEmployee.designation_title}</p>
                </div>
                <div>
                  <small style={{ color: 'var(--text-muted)' }}>Date of Joining</small>
                  <p>{selectedEmployee.date_of_joining}</p>
                </div>
                {selectedEmployee.basic_salary !== undefined && (
                  <div>
                    <small style={{ color: 'var(--text-muted)' }}>Basic Salary</small>
                    <p style={{ fontWeight: 700, color: 'var(--accent-emerald)' }}>
                      ${selectedEmployee.basic_salary.toLocaleString()}
                    </p>
                  </div>
                )}
                {selectedEmployee.allowances !== undefined && (
                  <div>
                    <small style={{ color: 'var(--text-muted)' }}>Allowances</small>
                    <p>${selectedEmployee.allowances.toLocaleString()}</p>
                  </div>
                )}
              </div>

              {/* Leave Balances */}
              {selectedEmployee.leave_balances && selectedEmployee.leave_balances.length > 0 && (
                <div style={{ marginBottom: '1.5rem' }}>
                  <h4 style={{ marginBottom: '0.75rem' }}>Leave Quota Balances</h4>
                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    {selectedEmployee.leave_balances.map((lb) => (
                      <div
                        key={lb.id}
                        style={{
                          background: 'rgba(255, 255, 255, 0.05)',
                          padding: '0.5rem 0.85rem',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-light)',
                        }}
                      >
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          {lb.leave_type?.name || 'Leave'}:
                        </span>{' '}
                        <strong>{lb.balance_days}</strong> / {lb.yearly_quota} days
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Self Edit Phone & Address */}
              <form onSubmit={handleUpdateSelf}>
                <h4 style={{ marginBottom: '0.75rem' }}>Contact Information (Editable)</h4>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Phone Number</label>
                    <input
                      type="text"
                      className="form-control"
                      value={editSelf.phone}
                      onChange={(e) => setEditSelf({ ...editSelf, phone: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Residential Address</label>
                    <input
                      type="text"
                      className="form-control"
                      value={editSelf.address}
                      onChange={(e) => setEditSelf({ ...editSelf, address: e.target.value })}
                    />
                  </div>
                </div>
                <button type="submit" className="btn btn-secondary btn-sm" disabled={submitting}>
                  Save Contact Info
                </button>
              </form>
            </div>
            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => setShowProfileModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CSV IMPORT MODAL WITH DRY RUN */}
      {showCsvModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog" style={{ maxWidth: '650px' }}>
            <div className="modal-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileSpreadsheet /> Import Employees from CSV
              </h3>
              <button className="btn-icon" onClick={() => setShowCsvModal(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: '0.85rem', marginBottom: '1rem' }}>
                Upload a CSV file containing: <code>employee_code, first_name, last_name, email, department_name, designation_title, date_of_joining, basic_salary, allowances, gender</code>.
              </p>

              <div className="form-group">
                <input
                  type="file"
                  accept=".csv"
                  className="form-control"
                  onChange={(e) => {
                    setCsvFile(e.target.files[0]);
                    setCsvDryRunResult(null);
                  }}
                />
              </div>

              {csvDryRunResult && (
                <div style={{ marginTop: '1rem' }}>
                  {csvDryRunResult.valid ? (
                    <div className="alert alert-success">
                      <CheckCircle2 size={18} />
                      <span>
                        Dry run passed! All {csvDryRunResult.total_rows} rows are valid and ready to import.
                      </span>
                    </div>
                  ) : (
                    <div>
                      <div className="alert alert-danger">
                        <AlertCircle size={18} />
                        <span>
                          Validation failed: {csvDryRunResult.errors?.length || 0} issues detected across rows.
                        </span>
                      </div>
                      <div className="table-responsive" style={{ maxHeight: '200px' }}>
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Row</th>
                              <th>Field</th>
                              <th>Reason</th>
                            </tr>
                          </thead>
                          <tbody>
                            {csvDryRunResult.errors?.map((err, idx) => (
                              <tr key={idx}>
                                <td>{err.row}</td>
                                <td><code>{err.field}</code></td>
                                <td>{err.reason}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowCsvModal(false)}
              >
                Close
              </button>

              <button
                type="button"
                className="btn btn-secondary"
                disabled={!csvFile || csvImporting}
                onClick={handleCsvDryRun}
              >
                {csvImporting ? 'Validating...' : 'Validate (Dry Run)'}
              </button>

              <button
                type="button"
                className="btn btn-primary"
                disabled={!csvFile || !csvDryRunResult?.valid || csvImporting}
                onClick={handleCsvFinalImport}
              >
                Confirm Import
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
