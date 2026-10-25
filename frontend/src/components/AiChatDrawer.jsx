import React, { useState, useRef, useEffect } from 'react';
import { aiService, getErrorMessage } from '../services/api';
import { Sparkles, Send, X, Bot, User, AlertCircle, RefreshCw } from 'lucide-react';

export const AiChatDrawer = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Hello! I am your HCM Lite AI Workforce Assistant. You can ask me questions about attendance, headcount, leave balances, or company policies in English or Roman Urdu.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput('');

    const newHistory = [...messages, { role: 'user', content: userText }];
    setMessages(newHistory);
    setLoading(true);

    try {
      // Call backend AI API with 15s client timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 16000);

      const res = await aiService.chat(userText, messages);
      clearTimeout(timeoutId);

      const reply = res.data?.response || res.data?.reply || 'I could not process that request.';
      setMessages([...newHistory, { role: 'assistant', content: reply }]);
    } catch (err) {
      let errorMsg =
        'Sorry, the AI Assistant is temporarily unavailable or timed out. Please try again in a moment.';
      if (err.name === 'AbortError' || err.code === 'ECONNABORTED') {
        errorMsg = 'Request timed out after 15 seconds. Please try again.';
      } else if (err.response?.status === 429) {
        errorMsg = 'Rate limit reached (20 requests per hour). Please try again shortly.';
      } else if (err.response?.data?.detail) {
        errorMsg = getErrorMessage(err);
      }
      setMessages([
        ...newHistory,
        {
          role: 'assistant',
          content: errorMsg,
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating launcher trigger */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 80,
          background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
          color: '#fff',
          border: 'none',
          borderRadius: '50px',
          padding: '0.75rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontWeight: 700,
          fontSize: '0.9rem',
          boxShadow: '0 4px 20px rgba(99, 102, 241, 0.5)',
          cursor: 'pointer',
          transition: 'transform var(--transition-fast), box-shadow var(--transition-fast)',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.transform = 'translateY(-2px)')}
        onMouseLeave={(e) => (e.currentTarget.style.transform = 'translateY(0)')}
      >
        <Sparkles size={18} />
        <span>Ask AI</span>
      </button>

      {/* Slide-over Chat Drawer */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '84px',
            right: '24px',
            width: '380px',
            maxWidth: 'calc(100vw - 32px)',
            height: '520px',
            maxHeight: 'calc(100vh - 110px)',
            background: '#111827',
            border: '1px solid rgba(99, 102, 241, 0.4)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.7), 0 0 25px rgba(99, 102, 241, 0.25)',
            zIndex: 90,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            animation: 'fadeIn 200ms ease-out',
          }}
        >
          {/* Drawer Header */}
          <div
            style={{
              padding: '1rem 1.25rem',
              background: 'linear-gradient(90deg, #1e1b4b, #0f172a)',
              borderBottom: '1px solid var(--border-light)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '6px',
                  background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                }}
              >
                <Bot size={16} />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#fff' }}>
                  Workforce Intelligence
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)' }}>
                  Gemini API • Role Scoped
                </div>
              </div>
            </div>
            <button
              className="btn-icon"
              style={{ width: '28px', height: '28px', padding: 0 }}
              onClick={() => setIsOpen(false)}
            >
              <X size={16} />
            </button>
          </div>

          {/* Messages Area */}
          <div
            style={{
              flex: 1,
              padding: '1rem',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.85rem',
            }}
          >
            {messages.map((m, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: m.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '85%',
                    padding: '0.75rem 0.95rem',
                    borderRadius: '12px',
                    fontSize: '0.88rem',
                    lineHeight: '1.45',
                    background:
                      m.role === 'user'
                        ? 'linear-gradient(135deg, #4f46e5, #4338ca)'
                        : 'rgba(30, 41, 59, 0.85)',
                    color: m.isError ? '#fca5a5' : '#f8fafc',
                    border:
                      m.role === 'user'
                        ? '1px solid rgba(99, 102, 241, 0.4)'
                        : '1px solid var(--border-light)',
                    boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
                  }}
                >
                  {m.content}
                </div>
                {m.role === 'assistant' && (
                  <span
                    style={{
                      fontSize: '0.65rem',
                      color: 'var(--text-muted)',
                      marginTop: '3px',
                      marginLeft: '4px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                    }}
                  >
                    AI-generated
                  </span>
                )}
              </div>
            ))}
            {loading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)' }}>
                <div className="spinner spinner-sm"></div>
                <span style={{ fontSize: '0.8rem' }}>Analyzing workforce data...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <form
            onSubmit={handleSend}
            style={{
              padding: '0.75rem 1rem',
              borderTop: '1px solid var(--border-light)',
              background: 'rgba(15, 23, 42, 0.8)',
              display: 'flex',
              gap: '0.5rem',
            }}
          >
            <input
              type="text"
              className="form-control"
              placeholder="Ask a question or request data..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              style={{ fontSize: '0.85rem', padding: '0.5rem 0.75rem' }}
            />
            <button
              type="submit"
              className="btn btn-primary btn-sm"
              disabled={loading || !input.trim()}
              style={{ padding: '0 0.85rem' }}
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      )}
    </>
  );
};
