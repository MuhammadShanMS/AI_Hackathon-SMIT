import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Turn any Axios error into a plain string so it is safe to render in React.
 * Handles Pydantic validation arrays, string details, and network errors.
 */
export function getErrorMessage(err) {
  if (!err) return 'An unexpected error occurred.';
  const data = err?.response?.data;
  if (data) {
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((e) => {
          if (typeof e === 'string') return e;
          if (e && typeof e === 'object') {
            const loc = Array.isArray(e.loc) ? e.loc.filter((l) => l !== 'body').join('.') : '';
            return loc ? `${loc}: ${e.msg || 'Invalid'}` : (e.msg || JSON.stringify(e));
          }
          return String(e);
        })
        .join('; ');
    }
    if (typeof data.detail === 'object' && data.detail !== null) {
      return JSON.stringify(data.detail);
    }
    if (typeof data === 'string') return data;
    if (data.message) return String(data.message);
  }
  if (typeof err === 'string') return err;
  if (err.message) return String(err.message);
  return 'An unexpected error occurred.';
}

// Attach JWT access token to outbound requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('hcm_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Global 401 interception
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('hcm_token');
      localStorage.removeItem('hcm_user');
      if (window.location.pathname !== '/login' && window.location.pathname !== '/setup') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const setupService = {
  getStatus: () => api.get('/setup/status'),
  setup: (payload) => api.post('/setup', payload),
};

export const authService = {
  // Backend expects JSON { email, password } – NOT OAuth2 form-data
  login: (email, password) => api.post('/auth/login', { email, password }),
  getMe: () => api.get('/auth/me'),
  changePassword: (current_password, new_password) =>
    api.post('/auth/change-password', { current_password, new_password }),
};

export const orgService = {
  getSettings: () => api.get('/org/settings'),
  updateSettings: (data) => api.put('/org/settings', data),
  getDepartments: () => api.get('/org/departments'),
  createDepartment: (data) => api.post('/org/departments', data),
  getDesignations: () => api.get('/org/designations'),
  createDesignation: (data) => api.post('/org/designations', data),
  getLeaveTypes: () => api.get('/org/leave-types'),
  createLeaveType: (data) => api.post('/org/leave-types', data),
  getHolidays: () => api.get('/org/holidays'),
  createHoliday: (data) => api.post('/org/holidays', data),
  createHrLogin: (email, password) =>
    api.post('/admin/users/hr', { email, password }),
};

export const adminService = {
  getUsers: () => api.get('/admin/users'),
  createHrLogin: (email, password) =>
    api.post('/admin/users/hr', { email, password }),
  updateUserStatus: (userId, isActive) =>
    api.patch(`/admin/users/${userId}/status`, { is_active: isActive }),
  resetUserPassword: (userId, temporary_password) =>
    api.post(`/admin/users/${userId}/reset-password`, { temporary_password }),
};

export const employeeService = {
  list: (params) => api.get('/employees', { params }),
  get: (id) => api.get(`/employees/${id}`),
  create: (data) => api.post('/employees', data),
  update: (id, data) => api.put(`/employees/${id}`, data),
  updateSelf: (data) => api.patch('/employees/me', data),
  exportCsv: () => api.get('/csv/export/employees', { responseType: 'blob' }),
  importCsv: (file, dryRun = true) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/csv/import/employees?dry_run=${dryRun}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export const attendanceService = {
  checkIn: (data = {}) => api.post('/attendance/check-in', data),
  checkOut: (data = {}) => api.post('/attendance/check-out', data),
  getCalendar: (params) => api.get('/attendance/calendar', { params }),
  getDailyBoard: (date) => api.get('/attendance/daily-board', { params: { date } }),
  requestCorrection: (data) => api.post('/attendance/corrections', data),
  listCorrections: () => api.get('/attendance/corrections'),
  reviewCorrection: (id, data) => api.patch(`/attendance/corrections/${id}/review`, data),
};

export const leaveService = {
  apply: (data) => api.post('/leaves', data),
  list: (params) => api.get('/leaves', { params }),
  getBalances: () => api.get('/leaves/balances'),
  cancel: (id) => api.post(`/leaves/${id}/cancel`),
  review: (id, data) => api.patch(`/leaves/${id}/review`, data),
};

export const payrollService = {
  createDraft: (month, year) => api.post('/payroll/draft', { month, year }),
  getRuns: () => api.get('/payroll/runs'),
  getRunDetails: (runId) => api.get(`/payroll/runs/${runId}`),
  finalizeRun: (runId) => api.post(`/payroll/runs/${runId}/finalize`),
  downloadPayslip: (employeeId, month, year) =>
    api.get(`/payroll/payslip/${employeeId}/${month}/${year}`, { responseType: 'blob' }),
};

export const dashboardService = {
  getHr: (params) => api.get('/dashboard/hr', { params }),
  getAdmin: (params) => api.get('/dashboard/admin', { params }),
  getEmployee: () => api.get('/dashboard/employee'),
};

export const commsService = {
  getAnnouncements: () => api.get('/announcements'),
  createAnnouncement: (data) => api.post('/announcements', data),
  getNotifications: () => api.get('/notifications'),
  markNotificationRead: (id) => api.patch(`/notifications/${id}/read`),
};

export const auditService = {
  getLogs: (params) => api.get('/audit', { params }),
};

export const aiService = {
  chat: (message, history = []) => api.post('/ai/chat', { message, history }),
  dashboardSummary: (kpiData) =>
    api.post('/ai/dashboard-summary', kpiData?.kpi_data ? kpiData : { kpi_data: kpiData }),
  smartLeave: (text) => api.post('/ai/smart-leave', { text }),
};

export default api;
