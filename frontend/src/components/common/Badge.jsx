import React from 'react';

export default function Badge({ variant = 'default', children, className = '', onClick }) {
  const baseStyle = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '3px 8px',
    borderRadius: 'var(--radius-sm)',
    fontSize: 'var(--text-xs)',
    fontWeight: '500',
    letterSpacing: '0.02em',
    cursor: onClick ? 'pointer' : 'default',
    transition: 'all 0.15s ease'
  };

  const variants = {
    default: {
      background: 'var(--surface-elevated)',
      color: 'var(--text-secondary)',
      border: '1px solid var(--border)'
    },
    verified: {
      background: 'var(--verified-bg)',
      color: 'var(--verified-text)',
      border: '1px solid var(--verified-border)'
    },
    flagged: {
      background: 'var(--flagged-bg)',
      color: 'var(--flagged-text)',
      border: '1px solid var(--flagged-border)'
    },
    rejected: {
      background: 'var(--rejected-bg)',
      color: 'var(--rejected-text)',
      border: '1px solid var(--rejected-border)'
    },
    gold: {
      background: 'rgba(201, 168, 76, 0.12)',
      color: 'var(--brand-accent)',
      border: '1px solid rgba(201, 168, 76, 0.35)'
    }
  };

  const currentVariant = variants[variant] || variants.default;

  return (
    <span
      style={{ ...baseStyle, ...currentVariant }}
      className={`halo-badge ${className}`}
      onClick={onClick}
    >
      {children}
    </span>
  );
}
