import React from 'react';

export default function PassageCard({ passage, onSelect, isActive = false }) {
  if (!passage) return null;

  const relevancePct = passage.relevance_score
    ? Math.round(passage.relevance_score <= 1.0 ? passage.relevance_score * 100 : passage.relevance_score)
    : 92;

  return (
    <div
      onClick={() => onSelect && onSelect(passage)}
      style={{
        padding: '12px 14px',
        backgroundColor: isActive ? 'var(--surface-elevated)' : 'var(--surface-card)',
        border: `1px solid ${isActive ? 'var(--brand-accent)' : 'var(--border)'}`,
        borderRadius: 'var(--radius-md)',
        cursor: 'pointer',
        transition: 'all 0.18s ease',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
      }}
      onMouseEnter={(e) => {
        if (!isActive) {
          e.currentTarget.style.borderColor = 'var(--brand-accent)';
          e.currentTarget.style.backgroundColor = 'var(--surface-elevated)';
        }
      }}
      onMouseLeave={(e) => {
        if (!isActive) {
          e.currentTarget.style.borderColor = 'var(--border)';
          e.currentTarget.style.backgroundColor = 'var(--surface-card)';
        }
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            color: 'var(--brand-accent)',
            backgroundColor: 'rgba(201, 168, 76, 0.1)',
            padding: '2px 6px',
            borderRadius: 'var(--radius-sm)'
          }}
        >
          {passage.passage_id || 'PASSAGE'}
        </span>

        <span
          style={{
            fontSize: 'var(--text-xs)',
            color: 'var(--verified-text)',
            fontWeight: '600'
          }}
        >
          {relevancePct}% Match
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <h4
          style={{
            fontSize: 'var(--text-sm)',
            fontWeight: '600',
            color: 'var(--text-primary)'
          }}
        >
          {passage.heading || passage.section || 'Authoritative Provision'}
        </h4>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
          {passage.source || 'Companies Act, 2013'}
        </span>
      </div>

      <p
        style={{
          fontSize: 'var(--text-xs)',
          color: 'var(--text-secondary)',
          lineHeight: '1.5',
          display: '-webkit-box',
          WebkitLineClamp: 3,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden'
        }}
      >
        {passage.text}
      </p>
    </div>
  );
}
