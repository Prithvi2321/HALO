import React, { useState } from 'react';

export default function Tooltip({ text, children, position = 'top' }) {
  const [visible, setVisible] = useState(false);

  return (
    <div
      style={{ position: 'relative', display: 'inline-flex' }}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && text && (
        <div
          className="animate-fade-in"
          style={{
            position: 'absolute',
            bottom: position === 'top' ? 'calc(100% + 6px)' : 'auto',
            top: position === 'bottom' ? 'calc(100% + 6px)' : 'auto',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'var(--surface-elevated)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            padding: '4px 8px',
            borderRadius: 'var(--radius-sm)',
            fontSize: 'var(--text-xs)',
            whiteSpace: 'nowrap',
            zIndex: 100,
            boxShadow: 'var(--shadow-md)',
            pointerEvents: 'none'
          }}
        >
          {text}
        </div>
      )}
    </div>
  );
}
