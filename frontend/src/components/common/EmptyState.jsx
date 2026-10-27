import React from 'react';

const SUGGESTED_QUERIES = [
  'What are director disqualifications under Section 164?',
  'Explain IBC Section 14 moratorium provisions against corporate debtor',
  'What is the minimum paid-up capital requirement for a public company?',
  'Under Section 135, what are the net worth and turnover thresholds for mandatory CSR?'
];

export default function EmptyState({ onSelectQuery }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-xl) var(--space-lg)',
        maxWidth: '720px',
        margin: '0 auto',
        textAlign: 'center',
        height: '100%'
      }}
      className="animate-fade-in"
    >
      <div
        style={{
          width: '64px',
          height: '64px',
          borderRadius: 'var(--radius-lg)',
          backgroundColor: 'rgba(201, 168, 76, 0.1)',
          border: '1px solid var(--border-strong)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: 'var(--space-md)'
        }}
      >
        <span style={{ fontSize: '32px', color: 'var(--brand-accent)' }}>⚖</span>
      </div>

      <h1
        style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'var(--text-2xl)',
          color: 'var(--text-gold)',
          fontWeight: '600',
          letterSpacing: '0.02em',
          marginBottom: '4px'
        }}
      >
        HALO
      </h1>
      <h2
        style={{
          fontSize: 'var(--text-sm)',
          color: 'var(--text-secondary)',
          fontWeight: '500',
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          marginBottom: 'var(--space-md)'
        }}
      >
        Nyaya Sahayak · Legal Assistant
      </h2>

      <p
        style={{
          color: 'var(--text-primary)',
          fontSize: 'var(--text-base)',
          maxWidth: '520px',
          marginBottom: 'var(--space-sm)'
        }}
      >
        Authoritative legal intelligence for Indian Corporate Law, the Companies Act 2013,
        and Supreme Court jurisprudence.
      </p>

      <p
        style={{
          fontSize: 'var(--text-sm)',
          color: 'var(--text-secondary)',
          marginBottom: 'var(--space-xl)'
        }}
      >
        Every answer is strictly decomposed into claims, verified against{' '}
        <span style={{ color: 'var(--verified-text)', fontWeight: '500' }}>12,223 authoritative passages</span>,
        and anchored with sentence-level citations.
      </p>

      <div style={{ width: '100%', textAlign: 'left' }}>
        <p
          style={{
            fontSize: 'var(--text-xs)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--text-muted)',
            marginBottom: 'var(--space-sm)',
            fontWeight: '600'
          }}
        >
          Suggested Research Inquiries
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
          {SUGGESTED_QUERIES.map((q, idx) => (
            <button
              key={idx}
              onClick={() => onSelectQuery && onSelectQuery(q)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                backgroundColor: 'var(--surface-card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-primary)',
                fontSize: 'var(--text-sm)',
                textAlign: 'left',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--surface-elevated)';
                e.currentTarget.style.borderColor = 'var(--brand-accent)';
                e.currentTarget.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--surface-card)';
                e.currentTarget.style.borderColor = 'var(--border)';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              <span>{q}</span>
              <span style={{ color: 'var(--brand-accent)', opacity: 0.8 }}>→</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
