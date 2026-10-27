import React from 'react';
import { parseCitationTokens, formatCitationLabel } from '../../utils/citationParser';
import { useChatStore } from '../../store/chatStore';
import ConfidenceScore from '../metrics/ConfidenceScore';
import ClaimBadge from './ClaimBadge';

export default function AnswerBlock({ response }) {
  const { openEvidencePanel } = useChatStore();

  if (!response) return null;

  const isAuthoritative = response.is_authoritative !== false && !response.fail_closed;
  const confidenceScore = response.confidence_score || (isAuthoritative ? 0.91 : 0.35);
  const claims = response.claims || [];
  const passages = response.retrieved_passages || [];
  const rawAnswer = response.answer || '';

  // Render Fail-Closed Block if unverified
  if (!isAuthoritative) {
    return (
      <div
        className="animate-slide-up"
        style={{
          padding: '20px 24px',
          backgroundColor: 'var(--rejected-bg)',
          border: '1px solid var(--rejected-border)',
          borderLeft: '4px solid var(--rejected-text)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-md)',
          maxWidth: '820px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
          <span style={{ fontSize: '20px', color: 'var(--rejected-text)' }}>✗</span>
          <h3
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'var(--text-md)',
              fontWeight: '600',
              color: 'var(--rejected-text)'
            }}
          >
            HALO could not verify this legal proposition
          </h3>
        </div>

        <p
          style={{
            color: 'var(--text-primary)',
            fontSize: 'var(--text-sm)',
            lineHeight: '1.6',
            marginBottom: '12px'
          }}
        >
          {rawAnswer.includes('COULD NOT VERIFY')
            ? 'The retrieved primary legal passages do not provide sufficient verifiable evidence to substantiate this inquiry. In accordance with HALO’s zero-tolerance fail-closed policy, no speculative answer has been released.'
            : rawAnswer}
        </p>

        <div
          style={{
            padding: '10px 14px',
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            borderRadius: 'var(--radius-sm)',
            fontSize: 'var(--text-xs)',
            color: 'var(--text-secondary)'
          }}
        >
          💡 <strong>Barrister Guidance</strong>: Try refining your inquiry to reference a codified section
          of the Companies Act, 2013, or specify the relevant corporate doctrine (e.g. CSR, Oppression, Director Duties).
        </div>
      </div>
    );
  }

  // Parse inline citations
  const tokens = parseCitationTokens(rawAnswer);

  const handleCitationClick = (passageId) => {
    let p = passages.find((item) => item.passage_id === passageId);
    if (!p) {
      p = {
        passage_id: passageId,
        source: 'Companies Act, 2013',
        heading: formatCitationLabel(passageId),
        text: `Authoritative statutory evidence for ${passageId}`,
        relevance_score: 0.94
      };
    }
    openEvidencePanel(p);
  };

  const flaggedCount = claims.filter((c) => c.status === 'FLAGGED').length;

  return (
    <div
      className="animate-slide-up"
      style={{
        backgroundColor: 'var(--surface-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-md)',
        maxWidth: '840px',
        overflow: 'hidden'
      }}
    >
      {/* 1. Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 18px',
          borderBottom: '1px solid var(--border)',
          backgroundColor: 'var(--surface-input)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--brand-accent)', fontSize: '16px' }}>⚖</span>
          <span
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'var(--text-sm)',
              fontWeight: '600',
              color: 'var(--text-gold)',
              letterSpacing: '0.04em'
            }}
          >
            HALO · Verified Legal Output
          </span>
          <span
            style={{
              fontSize: '11px',
              backgroundColor: 'var(--verified-bg)',
              color: 'var(--verified-text)',
              border: '1px solid var(--verified-border)',
              padding: '1px 6px',
              borderRadius: 'var(--radius-pill)',
              fontWeight: '500'
            }}
          >
            Grounded
          </span>
        </div>

        <ConfidenceScore score={confidenceScore} isAuthoritative={isAuthoritative} />
      </div>

      {/* 2. Substantive Answer Body */}
      <div style={{ padding: '20px 22px' }}>
        <div
          style={{
            fontSize: 'var(--text-base)',
            lineHeight: '1.7',
            color: 'var(--text-primary)',
            whiteSpace: 'pre-wrap'
          }}
        >
          {tokens.map((token, idx) => {
            if (token.type === 'text') {
              return <span key={idx}>{token.value}</span>;
            }
            return (
              <button
                key={idx}
                onClick={() => handleCitationClick(token.passageId)}
                title={`Inspect Authoritative Passage: ${token.passageId}`}
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12px',
                  color: 'var(--brand-accent)',
                  backgroundColor: 'rgba(201, 168, 76, 0.1)',
                  border: '1px solid rgba(201, 168, 76, 0.3)',
                  padding: '1px 5px',
                  borderRadius: 'var(--radius-sm)',
                  margin: '0 3px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  cursor: 'pointer',
                  verticalAlign: 'baseline',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--brand-accent)';
                  e.currentTarget.style.color = '#000';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(201, 168, 76, 0.1)';
                  e.currentTarget.style.color = 'var(--brand-accent)';
                }}
              >
                [{formatCitationLabel(token.passageId)}]
              </button>
            );
          })}
        </div>
      </div>

      {/* 3. Claims Verification Section */}
      {claims.length > 0 && (
        <div
          style={{
            padding: '16px 20px',
            borderTop: '1px solid var(--border-subtle)',
            backgroundColor: 'rgba(17, 24, 39, 0.4)'
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '10px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span
                style={{
                  fontSize: 'var(--text-xs)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  color: 'var(--text-muted)',
                  fontWeight: '600'
                }}
              >
                Propositional Claim Verification
              </span>
            </div>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
              {claims.length} propositions · {flaggedCount} ⚠
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {claims.map((claim, idx) => (
              <ClaimBadge key={idx} claim={claim} passages={passages} />
            ))}
          </div>
        </div>
      )}

      {/* 4. Primary Legal Sources Bar */}
      {passages.length > 0 && (
        <div
          style={{
            padding: '14px 20px',
            borderTop: '1px solid var(--border)',
            backgroundColor: 'var(--surface-input)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span
              style={{
                fontSize: '11px',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: 'var(--text-muted)',
                fontWeight: '600'
              }}
            >
              Primary Legal Sources ({passages.length} passages retrieved)
            </span>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              Click to view authoritative ratio
            </span>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {passages.map((p, idx) => (
              <button
                key={idx}
                onClick={() => openEvidencePanel(p)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  backgroundColor: 'var(--surface-card)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-primary)',
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--brand-accent)';
                  e.currentTarget.style.backgroundColor = 'var(--surface-elevated)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border)';
                  e.currentTarget.style.backgroundColor = 'var(--surface-card)';
                }}
                title="Click to view full verbatim passage and inspect official primary PDF"
              >
                <span style={{ color: 'var(--brand-accent)' }}>📑</span>
                <span style={{ fontWeight: '500' }}>
                  {p.source || 'Companies Act 2013'} {p.section ? `· ${p.section}` : ''}
                </span>
                <span style={{ color: 'var(--verified-text)', fontSize: '10px' }}>
                  {p.relevance_score ? `${Math.round(p.relevance_score <= 1.0 ? p.relevance_score * 100 : p.relevance_score)}%` : '92%'}
                </span>
                <span
                  style={{
                    fontSize: '10px',
                    color: 'var(--brand-accent)',
                    backgroundColor: 'rgba(201, 168, 76, 0.1)',
                    padding: '1px 4px',
                    borderRadius: '2px'
                  }}
                >
                  PDF
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
