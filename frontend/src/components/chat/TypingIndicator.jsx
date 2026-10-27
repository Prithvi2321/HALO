import React, { useState, useEffect } from 'react';

const STAGES = [
  '⚖ HALO is retrieving passages from 12,223 corpus...',
  '⚖ HALO is verifying claims against primary legal sources...',
  '⚖ HALO is anchoring sentence-level citations...'
];

export default function TypingIndicator() {
  const [stageIndex, setStageIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setStageIndex((prev) => (prev + 1) % STAGES.length);
    }, 1800);

    return () => clearInterval(timer);
  }, []);

  return (
    <div
      className="animate-slide-up"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '12px',
        padding: '12px 18px',
        backgroundColor: 'var(--surface-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-sm)',
        maxWidth: 'fit-content'
      }}
    >
      <div
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: 'var(--brand-accent)',
          boxShadow: '0 0 8px var(--brand-accent)'
        }}
        className="animate-pulse-glow"
      />

      <span
        key={stageIndex}
        className="animate-fade-in"
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--text-sm)',
          color: 'var(--brand-accent)',
          letterSpacing: '0.02em'
        }}
      >
        {STAGES[stageIndex]}
      </span>
    </div>
  );
}
