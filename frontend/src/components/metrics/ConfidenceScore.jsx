import React from 'react';
import { getConfidenceCircles, formatConfidence } from '../../utils/formatters';

export default function ConfidenceScore({ score = 0.91, isAuthoritative = true }) {
  const { filled, total } = getConfidenceCircles(score);
  const formattedPct = formatConfidence(score);

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        padding: '4px 10px',
        backgroundColor: isAuthoritative ? 'rgba(74, 222, 128, 0.08)' : 'rgba(248, 113, 113, 0.1)',
        border: `1px solid ${isAuthoritative ? 'var(--verified-border)' : 'var(--rejected-border)'}`,
        borderRadius: 'var(--radius-pill)',
        fontSize: 'var(--text-xs)',
        fontWeight: '500'
      }}
    >
      <span style={{ color: 'var(--text-secondary)' }}>Confidence:</span>
      <span
        style={{
          color: isAuthoritative ? 'var(--verified-text)' : 'var(--rejected-text)',
          letterSpacing: '2px',
          fontSize: '12px'
        }}
      >
        {[...Array(total)].map((_, i) => (
          <span
            key={i}
            style={{
              opacity: i < filled ? 1 : 0.25
            }}
          >
            ●
          </span>
        ))}
      </span>
      <span
        style={{
          color: isAuthoritative ? 'var(--verified-text)' : 'var(--rejected-text)',
          fontWeight: '600'
        }}
      >
        {formattedPct}
      </span>
    </div>
  );
}
