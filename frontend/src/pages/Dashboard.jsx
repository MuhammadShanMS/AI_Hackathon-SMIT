import React, { useState, useEffect } from 'react';
import { dashboardService, orgService, aiService, getErrorMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Users,
  Clock,
  CalendarCheck2,
  AlertTriangle,
  FileCheck,
  TrendingUp,
  DollarSign,
  UserX,
  Sparkles,
  PieChart as PieIcon,
  BarChart3,
  ShieldCheck,
  CheckCircle,
  X,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';

const COLORS = ['#6366f1', '#06b6d4', '#a855f7', '#f59e0b', '#10b981', '#f43f5e'];

export const Dashboard = () => {
  const { user, role } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState([]);

  // Filters
  const [deptFilter, setDeptFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // AI Summary state
  const [aiSummary, setAiSummary] = useState(null);
  const [summarizing, setSummarizing] = useState(false);

  useEffect(() => {
    fetchCatalogs();
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [role, deptFilter, startDate, endDate]);

  const fetchCatalogs = async () => {
    try {
      const res = await orgService.getDepartments();
      setDepartments(res.data || []);
    } catch (e) {}
  };

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      if (role === 'HR') {
        const res = await dashboardService.getHr({
          department_id: deptFilter || undefined,
          start_date: startDate || undefined,
          end_date: endDate || undefined,
        });
        setData(res.data);
      } else if (role === 'ADMIN') {
        const res = await dashboardService.getAdmin({
          department_id: deptFilter || undefined,
        });
        setData(res.data);
      } else {
        const res = await dashboardService.getEmployee();
        setData(res.data);
      }
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAiSummarize = async () => {
    if (!data) return;
    try {
      setSummarizing(true);
      const res = await aiService.dashboardSummary(data);
      setAiSummary(res.data?.insights || ['No insights generated.']);
    } catch (err) {
      alert(getErrorMessage(err));
    } finally {
      setSummarizing(false);
    }
  };

  if (loading && !data) {
    return (
      <div className="state-container" style={{ minHeight: '60vh' }}>
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div>
      {/* Dashboard Header */}
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
          <h2>
            {role === 'ADMIN'
              ? 'Executive Command Center'
              : role === 'HR'
              ? 'Human Resources Operational Intelligence'
              : 'My Workplace Portal'}
          </h2>
          <p>
            {role === 'ADMIN'
              ? 'High-level workforce health, payroll allocations, retention metrics, and compliance logs.'
              : role === 'HR'
              ? 'Daily attendance dynamics, pending requests, absenteeism rates, and leave trends.'
              : 'Track personal working hours, leave quotas, recent announcements, and compensation.'}
          </p>
        </div>

        {(role === 'HR' || role === 'ADMIN') && (
          <button
            className="btn btn-primary"
            onClick={handleAiSummarize}
            disabled={summarizing}
            style={{
              background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
              boxShadow: '0 0 15px rgba(6, 182, 212, 0.4)',
            }}
          >
            <Sparkles size={16} />
            {summarizing ? 'Generating AI Insights...' : 'Summarize with AI'}
          </button>
        )}
      </div>

      {/* AI Insights Card Modal/Banner */}
      {aiSummary && (
        <div
          className="card"
          style={{
            marginBottom: '1.5rem',
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(6, 182, 212, 0.1))',
            borderColor: 'rgba(99, 102, 241, 0.4)',
            boxShadow: '0 0 20px rgba(99, 102, 241, 0.2)',
          }}
        >
          <div className="card-header" style={{ marginBottom: '0.75rem' }}>
            <h3 className="card-title" style={{ fontSize: '1.05rem', color: 'var(--accent-cyan)' }}>
              <Sparkles size={18} /> Executive AI Intelligence Briefing
            </h3>
            <button className="btn-icon" onClick={() => setAiSummary(null)}>
              <X size={16} />
            </button>
          </div>
          <ul style={{ paddingLeft: '1.25rem', lineHeight: '1.7' }}>
            {aiSummary.map((item, idx) => (
              <li key={idx} style={{ color: 'var(--text-primary)', fontSize: '0.92rem' }}>
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Filters Bar for HR & Admin */}
      {(role === 'HR' || role === 'ADMIN') && (
        <div className="card" style={{ marginBottom: '1.5rem', padding: '0.85rem 1.25rem' }}>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ minWidth: '200px' }}>
              <select
                className="form-control"
                value={deptFilter}
                onChange={(e) => setDeptFilter(e.target.value)}
              >
                <option value="">All Departments</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            {role === 'HR' && (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>From:</span>
                  <input
                    type="date"
                    className="form-control"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>To:</span>
                  <input
                    type="date"
                    className="form-control"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              </>
            )}

            {(deptFilter || startDate || endDate) && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  setDeptFilter('');
                  setStartDate('');
                  setEndDate('');
                }}
              >
                Reset Filters
              </button>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* HR DASHBOARD VIEW */}
      {/* ========================================================================= */}
      {role === 'HR' && data && (
        <div>
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-label">Headcount</span>
              <span className="metric-value">{data.headcount || 0}</span>
              <span className="metric-sub">Active staff members</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Present Today</span>
              <span className="metric-value" style={{ color: 'var(--status-success)' }}>
                {data.present_today || 0}
              </span>
              <span className="metric-sub">Checked in on campus</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">On Leave</span>
              <span className="metric-value" style={{ color: 'var(--accent-cyan)' }}>
                {data.on_leave || 0}
              </span>
              <span className="metric-sub">Approved time-off</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Late Arrivals</span>
              <span className="metric-value" style={{ color: 'var(--accent-amber)' }}>
                {data.late_today || 0}
              </span>
              <span className="metric-sub">Late: {data.late_percentage?.toFixed(1) || 0}%</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Pending Approvals</span>
              <span className="metric-value" style={{ color: 'var(--accent-purple)' }}>
                {data.pending_approvals || 0}
              </span>
              <span className="metric-sub">Leaves & corrections</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Attendance Rate</span>
              <span className="metric-value" style={{ color: 'var(--accent-emerald)' }}>
                {data.attendance_rate?.toFixed(1) || 0}%
              </span>
              <span className="metric-sub">Working-day presence</span>
            </div>
          </div>

          {/* Charts Row */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
              gap: '1.5rem',
              marginBottom: '1.5rem',
            }}
          >
            {/* 14-Day Attendance Trend */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <TrendingUp size={18} /> 14-Day Attendance Trend
                </h3>
              </div>
              <div style={{ height: '240px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.attendance_trend || []}>
                    <defs>
                      <linearGradient id="colorPresent" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        background: '#131b2e',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 8,
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="present"
                      stroke="#6366f1"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorPresent)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Absenteeism by Dept */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <BarChart3 size={18} /> Absenteeism Rate by Department (%)
                </h3>
              </div>
              <div style={{ height: '240px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.absenteeism_by_dept || []}>
                    <XAxis dataKey="department" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        background: '#131b2e',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 8,
                      }}
                    />
                    <Bar dataKey="rate" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Top 5 Late Comers & Leave by Type */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
              gap: '1.5rem',
            }}
          >
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <AlertTriangle size={18} color="var(--accent-amber)" /> Top Late-Comers
                </h3>
              </div>
              {(data.top_5_late_comers || []).length === 0 ? (
                <p style={{ color: 'var(--text-muted)' }}>No late records logged.</p>
              ) : (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Employee</th>
                        <th>Late Occurrences</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.top_5_late_comers.map((c, i) => (
                        <tr key={i}>
                          <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                            {c.employee_name}
                          </td>
                          <td style={{ color: 'var(--accent-amber)', fontWeight: 700 }}>
                            {c.count} times
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <PieIcon size={18} /> Leave Distribution by Type
                </h3>
              </div>
              <div style={{ height: '200px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data.leave_by_type || []}
                      dataKey="days"
                      nameKey="type"
                      cx="50%"
                      cy="50%"
                      outerRadius={75}
                      label
                    >
                      {(data.leave_by_type || []).map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: '#131b2e',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 8,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* ADMIN DASHBOARD VIEW */}
      {/* ========================================================================= */}
      {role === 'ADMIN' && data && (
        <div>
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-label">Total Headcount</span>
              <span className="metric-value">{data.headcount || 0}</span>
              <span className="metric-sub">Total active headcount</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Attrition Rate YTD</span>
              <span className="metric-value" style={{ color: 'var(--status-danger)' }}>
                {data.attrition_ytd?.toFixed(1) || 0}%
              </span>
              <span className="metric-sub">Exits vs avg headcount</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Monthly Payroll Cost</span>
              <span className="metric-value" style={{ color: 'var(--accent-emerald)' }}>
                ${data.payroll_cost?.toLocaleString() || 0}
              </span>
              <span className="metric-sub">Gross compensation load</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Average Salary</span>
              <span className="metric-value" style={{ color: 'var(--accent-cyan)' }}>
                ${data.average_salary?.toLocaleString() || 0}
              </span>
              <span className="metric-sub">Per employee mean</span>
            </div>
          </div>

          {/* Department Breakdown Charts */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
              gap: '1.5rem',
              marginBottom: '1.5rem',
            }}
          >
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <Users size={18} /> Headcount by Department
                </h3>
              </div>
              <div style={{ height: '240px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.headcount_by_dept || []}>
                    <XAxis dataKey="department" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        background: '#131b2e',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 8,
                      }}
                    />
                    <Bar dataKey="headcount" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <DollarSign size={18} /> Payroll Cost by Department ($)
                </h3>
              </div>
              <div style={{ height: '240px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.payroll_cost_by_dept || []}>
                    <XAxis dataKey="department" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        background: '#131b2e',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 8,
                      }}
                    />
                    <Bar dataKey="cost" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Demographics & Recent Audit Log */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
              gap: '1.5rem',
            }}
          >
            {/* Gender and Tenure */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Demographics & Tenure</h3>
              </div>
              <div style={{ marginBottom: '1.25rem' }}>
                <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 8 }}>
                  Gender Distribution:
                </h4>
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                  {Object.entries(data.gender_distribution || {}).map(([g, count]) => (
                    <div
                      key={g}
                      style={{
                        padding: '0.4rem 0.75rem',
                        background: 'rgba(255,255,255,0.05)',
                        borderRadius: 'var(--radius-sm)',
                      }}
                    >
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{g}:</span>{' '}
                      <strong>{count}</strong>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 8 }}>
                  Tenure Breakdown:
                </h4>
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                  {Object.entries(data.tenure_breakdown || {}).map(([t, count]) => (
                    <div
                      key={t}
                      style={{
                        padding: '0.4rem 0.75rem',
                        background: 'rgba(255,255,255,0.05)',
                        borderRadius: 'var(--radius-sm)',
                      }}
                    >
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{t}:</span>{' '}
                      <strong>{count}</strong>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Last 10 Audit Logs */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <ShieldCheck size={18} /> Last 10 Audit Trail Entries
                </h3>
              </div>
              <div className="table-responsive" style={{ maxHeight: '250px' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Action</th>
                      <th>Target</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.last_10_audit_entries || []).map((log, idx) => (
                      <tr key={idx}>
                        <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {log.action}
                        </td>
                        <td>
                          {log.target_type} #{log.target_id}
                        </td>
                        <td style={{ fontSize: '0.75rem' }}>
                          {new Date(log.created_at).toLocaleTimeString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* EMPLOYEE DASHBOARD VIEW */}
      {/* ========================================================================= */}
      {role === 'EMPLOYEE' && data && (
        <div>
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-label">Hours This Week</span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem' }}>
                <span className="metric-value" style={{ color: 'var(--accent-cyan)' }}>
                  {data.hours_this_week?.toFixed(1) || 0}h
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>/ 40h standard</span>
              </div>
              <div
                style={{
                  height: '6px',
                  background: 'rgba(255,255,255,0.1)',
                  borderRadius: 4,
                  marginTop: '0.75rem',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${Math.min(100, ((data.hours_this_week || 0) / 40) * 100)}%`,
                    background: 'linear-gradient(90deg, #6366f1, #06b6d4)',
                  }}
                />
              </div>
            </div>

            <div className="metric-card">
              <span className="metric-label">Late Count (This Month)</span>
              <span className="metric-value" style={{ color: 'var(--accent-amber)' }}>
                {data.late_count || 0}
              </span>
              <span className="metric-sub">Grace window adherence</span>
            </div>

            <div className="metric-card">
              <span className="metric-label">Latest Net Pay</span>
              <span className="metric-value" style={{ color: 'var(--accent-emerald)' }}>
                {data.last_payslip
                  ? `$${data.last_payslip.net_salary?.toLocaleString()}`
                  : 'N/A'}
              </span>
              <span className="metric-sub">
                {data.last_payslip
                  ? `${data.last_payslip.year}-${data.last_payslip.month}`
                  : 'No payslip issued'}
              </span>
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
              gap: '1.5rem',
              marginTop: '1.5rem',
            }}
          >
            {/* Leave Balances Breakdown */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Leave Quotas</h3>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {(data.leave_balances || []).map((b) => (
                  <div
                    key={b.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.5rem 0.75rem',
                      background: 'rgba(255,255,255,0.03)',
                      borderRadius: 'var(--radius-sm)',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {b.leave_type_name}
                      </div>
                      <small style={{ color: 'var(--text-muted)' }}>
                        Used {b.used_days} of {b.yearly_quota} days
                      </small>
                    </div>
                    <span
                      style={{
                        fontWeight: 700,
                        fontSize: '1.1rem',
                        color: 'var(--accent-cyan)',
                      }}
                    >
                      {b.balance_days} left
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Announcements */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Recent Broadcasts</h3>
              </div>
              {(data.announcements || []).length === 0 ? (
                <p style={{ color: 'var(--text-muted)' }}>No broadcasts posted yet.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {data.announcements.slice(0, 3).map((a) => (
                    <div
                      key={a.id}
                      style={{
                        padding: '0.75rem',
                        background: 'rgba(255,255,255,0.03)',
                        borderRadius: 'var(--radius-sm)',
                        borderLeft: '3px solid var(--primary-500)',
                      }}
                    >
                      <h4 style={{ fontSize: '0.95rem' }}>{a.title}</h4>
                      <p style={{ fontSize: '0.85rem', marginTop: 4 }}>{a.body}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
