import React from 'react';
import ConfidenceScore from './ConfidenceScore';

export default function MetricsBar({
  confidenceScore = 0.91,
  isAuthoritative = true,
  citationsCount = 0,
  retrievalTimeMs = 320
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 'var(--space-sm)',
        padding: '8px 14px',
        backgroundColor: 'var(--surface-input)',
        borderBottom: '1px solid var(--border)',
        fontSize: 'var(--text-xs)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--brand-accent)' }}>⚖</span>
          <span style={{ color: 'var(--text-secondary)' }}>Status:</span>
          <span
            style={{
              color: isAuthoritative ? 'var(--verified-text)' : 'var(--rejected-text)',
              fontWeight: '600'
            }}
          >
            {isAuthoritative ? 'Authoritative Grounded' : 'Refused / Fail-Closed'}
          </span>
        </div>

        {citationsCount > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Citations:</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: '600' }}>
              {citationsCount} Passages
            </span>
          </div>
        )}

        {retrievalTimeMs && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Latency:</span>
            <span style={{ color: 'var(--text-muted)' }}>{retrievalTimeMs}ms</span>
          </div>
        )}
      </div>

      <ConfidenceScore score={confidenceScore} isAuthoritative={isAuthoritative} />
    </div>
  );
}
