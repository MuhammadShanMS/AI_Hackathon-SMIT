import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: String(error?.message || error) };
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary]', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh', display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          background: '#0f1117', color: '#fff', fontFamily: 'Inter, sans-serif', gap: 16,
        }}>
          <h2 style={{ color: '#ff6b6b' }}>Something went wrong</h2>
          <p style={{ color: '#aaa', maxWidth: 480, textAlign: 'center' }}>{this.state.message}</p>
          <button
            onClick={() => { this.setState({ hasError: false }); window.location.href = '/'; }}
            style={{
              padding: '10px 24px', borderRadius: 8, border: 'none',
              background: '#6c63ff', color: '#fff', cursor: 'pointer', fontSize: 15,
            }}
          >
            Go to Home
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
