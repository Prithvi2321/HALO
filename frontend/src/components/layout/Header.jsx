import React from 'react';
import { useChatStore } from '../../store/chatStore';

export default function Header() {
  const { corpusStats } = useChatStore();

  return (
    <header
      style={{
        height: '60px',
        backgroundColor: 'var(--surface-sidebar)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        zIndex: 20
      }}
    >
      {/* Left: Branding */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            width: '34px',
            height: '34px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'rgba(201, 168, 76, 0.12)',
            border: '1px solid var(--border-strong)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--brand-accent)',
            fontSize: '18px'
          }}
        >
          ⚖
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 'var(--text-lg)',
                color: 'var(--text-gold)',
                fontWeight: '600',
                letterSpacing: '0.04em'
              }}
            >
              HALO
            </span>
            <span
              style={{
                fontSize: 'var(--text-xs)',
                color: 'var(--text-secondary)',
                fontWeight: '500',
                letterSpacing: '0.08em',
                textTransform: 'uppercase'
              }}
            >
              Nyaya Sahayak
            </span>
          </div>
        </div>
      </div>

      {/* Right: Active Corpus Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '5px 12px',
            backgroundColor: 'var(--surface-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-pill)',
            fontSize: 'var(--text-xs)'
          }}
        >
          <div
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: 'var(--verified-text)'
            }}
            className="animate-pulse-glow"
          />
          <span style={{ color: 'var(--verified-text)', fontWeight: '600' }}>
            Corpus Active
          </span>
          <span style={{ color: 'var(--text-muted)' }}>|</span>
          <span style={{ color: 'var(--text-secondary)' }}>
            {(corpusStats?.total_passages || 12223).toLocaleString()} passages indexed
          </span>
        </div>
      </div>
    </header>
  );
}
