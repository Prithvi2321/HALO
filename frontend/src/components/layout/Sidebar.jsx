import React, { useEffect } from 'react';
import { useChatStore } from '../../store/chatStore';
import { formatDate } from '../../utils/formatters';
import { fetchHistory } from '../../services/historyService';

export default function Sidebar() {
  const {
    sessions,
    activeSessionId,
    corpusStats,
    createNewSession,
    loadSession,
    removeSession,
    setSessions
  } = useChatStore();

  useEffect(() => {
    async function loadSessions() {
      const serverSessions = await fetchHistory();
      if (serverSessions && serverSessions.length > 0) {
        setSessions(serverSessions);
      }
    }
    loadSessions();
  }, [setSessions]);

  // Group sessions by Today / Yesterday / Older
  const groupedSessions = {
    today: [],
    yesterday: [],
    older: []
  };

  const now = new Date();
  sessions.forEach((s) => {
    const sDate = new Date(s.timestamp || Date.now());
    const diffDays = Math.floor((now - sDate) / (1000 * 60 * 60 * 24));
    if (diffDays === 0) groupedSessions.today.push(s);
    else if (diffDays === 1) groupedSessions.yesterday.push(s);
    else groupedSessions.older.push(s);
  });

  return (
    <aside
      style={{
        width: '260px',
        height: '100%',
        backgroundColor: 'var(--surface-sidebar)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 30,
        flexShrink: 0
      }}
    >
      {/* Top Header & New Research Button */}
      <div
        style={{
          padding: '18px 16px 14px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '20px', color: 'var(--brand-accent)' }}>⚖</span>
          <div>
            <span
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 'var(--text-lg)',
                color: 'var(--text-gold)',
                fontWeight: '600'
              }}
            >
              HALO
            </span>
            <span
              style={{
                display: 'block',
                fontSize: '10px',
                color: 'var(--text-secondary)',
                letterSpacing: '0.1em',
                textTransform: 'uppercase'
              }}
            >
              Nyaya Sahayak
            </span>
          </div>
        </div>

        {/* New Research Button (Gold border, not filled - Section 5.2) */}
        <button
          onClick={createNewSession}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            width: '100%',
            padding: '9px 12px',
            backgroundColor: 'transparent',
            border: '1px solid var(--brand-accent)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--text-gold)',
            fontSize: 'var(--text-sm)',
            fontWeight: '500',
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'rgba(201, 168, 76, 0.12)';
            e.currentTarget.style.boxShadow = 'var(--shadow-gold)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.boxShadow = 'none';
          }}
        >
          <span style={{ fontSize: '16px', lineHeight: 1 }}>+</span>
          <span>New Research</span>
        </button>
      </div>

      {/* Middle: Scrollable Query History */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '14px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}
      >
        {sessions.length === 0 ? (
          <div style={{ padding: '24px 8px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>
            No prior research queries recorded in this session.
          </div>
        ) : (
          <>
            {groupedSessions.today.length > 0 && (
              <div>
                <p
                  style={{
                    fontSize: '10px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                    color: 'var(--text-muted)',
                    fontWeight: '600',
                    padding: '0 8px 6px'
                  }}
                >
                  Today
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                  {groupedSessions.today.map((s) => (
                    <HistoryItem
                      key={s.session_id}
                      session={s}
                      isActive={s.session_id === activeSessionId}
                      onSelect={() => loadSession(s.session_id)}
                      onDelete={(e) => {
                        e.stopPropagation();
                        removeSession(s.session_id);
                      }}
                    />
                  ))}
                </div>
              </div>
            )}

            {groupedSessions.yesterday.length > 0 && (
              <div>
                <p
                  style={{
                    fontSize: '10px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                    color: 'var(--text-muted)',
                    fontWeight: '600',
                    padding: '0 8px 6px'
                  }}
                >
                  Yesterday
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                  {groupedSessions.yesterday.map((s) => (
                    <HistoryItem
                      key={s.session_id}
                      session={s}
                      isActive={s.session_id === activeSessionId}
                      onSelect={() => loadSession(s.session_id)}
                      onDelete={(e) => {
                        e.stopPropagation();
                        removeSession(s.session_id);
                      }}
                    />
                  ))}
                </div>
              </div>
            )}

            {groupedSessions.older.length > 0 && (
              <div>
                <p
                  style={{
                    fontSize: '10px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                    color: 'var(--text-muted)',
                    fontWeight: '600',
                    padding: '0 8px 6px'
                  }}
                >
                  Previous Research
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                  {groupedSessions.older.map((s) => (
                    <HistoryItem
                      key={s.session_id}
                      session={s}
                      isActive={s.session_id === activeSessionId}
                      onSelect={() => loadSession(s.session_id)}
                      onDelete={(e) => {
                        e.stopPropagation();
                        removeSession(s.session_id);
                      }}
                    />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Bottom Pinned: Corpus Stats Footer (Section 5.2 & Rule 6) */}
      <div
        style={{
          padding: '14px 16px',
          borderTop: '1px solid var(--border)',
          backgroundColor: 'var(--surface-card)',
          fontSize: 'var(--text-xs)',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-secondary)', fontWeight: '500' }}>Active Knowledge Base</span>
          <span style={{ color: 'var(--verified-text)', fontSize: '10px' }}>● 100% Verified</span>
        </div>
        <p
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            color: 'var(--text-muted)',
            lineHeight: '1.4'
          }}
        >
          {(corpusStats?.total_passages || 12223).toLocaleString()} passages ·{' '}
          {corpusStats?.acts_count || 470} sections ·{' '}
          {corpusStats?.judgments_count || 854} judgments
        </p>
      </div>
    </aside>
  );
}

function HistoryItem({ session, isActive, onSelect, onDelete }) {
  const [hovered, setHovered] = React.useState(false);

  return (
    <div
      onClick={onSelect}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        width: '100%',
        padding: '8px 10px',
        borderRadius: 'var(--radius-sm)',
        backgroundColor: isActive ? 'var(--surface-elevated)' : (hovered ? 'rgba(36, 52, 71, 0.4)' : 'transparent'),
        borderLeft: isActive ? '3px solid var(--brand-accent)' : '3px solid transparent',
        color: isActive ? 'var(--text-primary)' : (hovered ? 'var(--text-primary)' : 'var(--text-secondary)'),
        fontSize: 'var(--text-xs)',
        textAlign: 'left',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        overflow: 'hidden'
      }}
    >
      <span
        style={{
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          flex: 1
        }}
        title={session.title}
      >
        {session.title || 'Legal Research Session'}
      </span>

      {hovered && (
        <button
          onClick={onDelete}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '2px 4px',
            fontSize: '11px',
            lineHeight: 1,
            borderRadius: '2px'
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--rejected-text)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
          title="Delete session"
        >
          ✕
        </button>
      )}
    </div>
  );
}
