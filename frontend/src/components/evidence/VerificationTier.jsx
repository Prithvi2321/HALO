import React from 'react';

export default function VerificationTier({ tier = 3, isPassed = true }) {
  const tiers = [
    {
      num: 1,
      name: 'Citation Existence',
      desc: '3-tier canonical legal citation validation (AIR, SCC, SCR, MCA)'
    },
    {
      num: 2,
      name: 'NLI Passage Entailment',
      desc: 'Substantive sentence-level bidirectional entailment against passage'
    },
    {
      num: 3,
      name: 'Temporal Enforceability',
      desc: '2015-2020 MCA amendments and judicial enforceability check'
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <p
        style={{
          fontSize: 'var(--text-xs)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: 'var(--text-muted)',
          fontWeight: '600'
        }}
      >
        HALO Verification Tiers
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {tiers.map((t) => {
          const active = t.num <= tier && isPassed;
          return (
            <div
              key={t.num}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 10px',
                backgroundColor: active ? 'var(--verified-bg)' : 'var(--surface-input)',
                border: `1px solid ${active ? 'var(--verified-border)' : 'var(--border)'}`,
                borderRadius: 'var(--radius-sm)',
                fontSize: 'var(--text-xs)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span
                  style={{
                    color: active ? 'var(--verified-text)' : 'var(--text-muted)',
                    fontWeight: 'bold'
                  }}
                >
                  {active ? '✓' : '○'}
                </span>
                <span
                  style={{
                    color: active ? 'var(--verified-text)' : 'var(--text-secondary)',
                    fontWeight: '500'
                  }}
                >
                  Tier {t.num}: {t.name}
                </span>
              </div>
              <span
                style={{
                  fontSize: '10px',
                  color: active ? 'var(--verified-text)' : 'var(--text-muted)',
                  textTransform: 'uppercase',
                  fontWeight: '600'
                }}
              >
                {active ? 'Passed' : 'Pending'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
