import React, { useState, useRef, useEffect } from 'react';

export default function QueryInput({ onSendMessage, disabled = false }) {
  const [query, setQuery] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || disabled) return;

    onSendMessage(trimmed);
    setQuery('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      style={{
        padding: '16px 24px 20px',
        backgroundColor: 'var(--surface-bg)',
        borderTop: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        width: '100%',
        maxWidth: '880px',
        margin: '0 auto'
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          backgroundColor: 'var(--surface-input)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          padding: '6px 12px 6px 16px',
          boxShadow: 'var(--shadow-sm)',
          transition: 'all 0.2s ease'
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = 'var(--brand-accent)';
          e.currentTarget.style.boxShadow = '0 0 0 2px var(--brand-accent-glow)';
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = 'var(--border)';
          e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
        }}
      >
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about Companies Act, IBC, or SC judgments..."
          disabled={disabled}
          rows={1}
          style={{
            flex: 1,
            backgroundColor: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text-primary)',
            fontSize: 'var(--text-base)',
            lineHeight: '1.4',
            resize: 'none',
            maxHeight: '120px',
            padding: '6px 0'
          }}
        />

        <button
          type="submit"
          disabled={!query.trim() || disabled}
          style={{
            width: '36px',
            height: '36px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: query.trim() && !disabled ? 'var(--brand-accent)' : 'var(--surface-elevated)',
            color: query.trim() && !disabled ? '#0D1117' : 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: query.trim() && !disabled ? 'pointer' : 'not-allowed',
            transition: 'all 0.2s ease',
            flexShrink: 0,
            marginLeft: '8px'
          }}
          onMouseEnter={(e) => {
            if (query.trim() && !disabled) {
              e.currentTarget.style.filter = 'brightness(1.15)';
              e.currentTarget.style.transform = 'scale(1.05)';
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.filter = 'none';
            e.currentTarget.style.transform = 'scale(1)';
          }}
          title="Execute Legal Query"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="12" y1="19" x2="12" y2="5"></line>
            <polyline points="5 12 12 5 19 12"></polyline>
          </svg>
        </button>
      </form>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          marginTop: '8px',
          fontSize: '11px',
          color: 'var(--text-muted)'
        }}
      >
        <span>⚖ Searching 12,223 passages</span>
        <span>·</span>
        <span style={{ color: 'var(--verified-text)' }}>● Verification active</span>
        <span>·</span>
        <span>Fail-closed governance</span>
      </div>
    </div>
  );
}
