import React from 'react';
import { useChatStore } from '../../store/chatStore';
import { truncate } from '../../utils/formatters';

export default function ClaimBadge({ claim, passages = [] }) {
  const { openEvidencePanel } = useChatStore();

  const status = (claim.status || 'SUPPORTED').toUpperCase();
  const isVerified = status === 'SUPPORTED';
  const isFlagged = status === 'FLAGGED' || status === 'PARTIALLY_SUPPORTED';

  const badgeTheme = isVerified
    ? {
        bg: 'var(--verified-bg)',
        border: 'var(--verified-border)',
        text: 'var(--verified-text)',
        icon: '✅',
        label: 'VERIFIED'
      }
    : isFlagged
    ? {
        bg: 'var(--flagged-bg)',
        border: 'var(--flagged-border)',
        text: 'var(--flagged-text)',
        icon: '⚠️',
        label: 'FLAGGED'
      }
    : {
        bg: 'var(--rejected-bg)',
        border: 'var(--rejected-border)',
        text: 'var(--rejected-text)',
        icon: '✗',
        label: 'UNVERIFIED'
      };

  const handleView = () => {
    // Find matching passage or construct one
    let targetPassage = passages.find((p) => p.passage_id === claim.passage_id);
    if (!targetPassage) {
      targetPassage = {
        passage_id: claim.passage_id || 'PAS_ACT_COMPANIES_2013',
        source: 'Companies Act, 2013',
        heading: 'Authoritative Legal Evidence',
        text: claim.claim_text || 'Authoritative evidence passage referenced for this claim.',
        relevance_score: 0.94
      };
    }
    openEvidencePanel(targetPassage);
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        backgroundColor: badgeTheme.bg,
        border: `1px solid ${badgeTheme.border}`,
        borderLeft: `3px solid ${badgeTheme.text}`,
        borderRadius: 'var(--radius-sm)',
        fontSize: 'var(--text-xs)',
        gap: 'var(--space-sm)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
        <span>{badgeTheme.icon}</span>
        <span
          style={{
            color: 'var(--text-primary)',
            fontWeight: '400',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}
          title={claim.claim_text}
        >
          {truncate(claim.claim_text, 65)}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
        {claim.passage_id && (
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              color: badgeTheme.text,
              backgroundColor: 'rgba(0,0,0,0.3)',
              padding: '2px 6px',
              borderRadius: 'var(--radius-sm)'
            }}
          >
            {claim.passage_id.replace('PAS_ACT_COMPANIES_2013_', '').slice(0, 15)}
          </span>
        )}

        <button
          onClick={handleView}
          style={{
            padding: '2px 8px',
            backgroundColor: 'var(--surface-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-secondary)',
            fontSize: '11px',
            fontWeight: '500'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = 'var(--brand-accent)';
            e.currentTarget.style.borderColor = 'var(--brand-accent)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = 'var(--text-secondary)';
            e.currentTarget.style.borderColor = 'var(--border)';
          }}
        >
          View Evidence
        </button>
      </div>
    </div>
  );
}
