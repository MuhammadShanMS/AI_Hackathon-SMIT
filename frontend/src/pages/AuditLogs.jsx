import React, { useState, useEffect } from 'react';
import { auditService } from '../services/api';
import { ShieldCheck, Search, Filter } from 'lucide-react';

export const AuditLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [page, setPage] = useState(1);
  const [limit] = useState(25);

  useEffect(() => {
    fetchLogs();
  }, [actionFilter, page]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const { data } = await auditService.getLogs({
        action: actionFilter || undefined,
        limit,
        offset: (page - 1) * limit,
      });
      setLogs(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '1.75rem' }}>
        <h2>System Security & Compliance Audit Log</h2>
        <p>Immutable forensic record of all administrative, financial, and organizational operations.</p>
      </div>

      <div className="card" style={{ marginBottom: '1.5rem', padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div style={{ minWidth: '240px' }}>
            <input
              type="text"
              className="form-control"
              placeholder="Filter by action (e.g. CREATE, LOGIN)..."
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                setPage(1);
              }}
            />
          </div>
        </div>
      </div>

      <div className="card">
        {loading ? (
          <div className="state-container">
            <div className="spinner"></div>
          </div>
        ) : logs.length === 0 ? (
          <div className="state-container">
            <ShieldCheck size={32} color="var(--text-muted)" style={{ marginBottom: 12 }} />
            <h3>No audit logs match criteria</h3>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>User ID</th>
                  <th>Action</th>
                  <th>Target Type</th>
                  <th>Target ID</th>
                  <th>IP Address</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td style={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {log.user_id ? `User #${log.user_id}` : 'System'}
                    </td>
                    <td>
                      <span className="badge badge-locked">{log.action}</span>
                    </td>
                    <td>{log.target_type}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>#{log.target_id}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                      {log.ip_address || '-'}
                    </td>
                    <td style={{ fontSize: '0.8rem', maxWidth: '300px', wordBreak: 'break-all' }}>
                      {log.details ? JSON.stringify(log.details) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
