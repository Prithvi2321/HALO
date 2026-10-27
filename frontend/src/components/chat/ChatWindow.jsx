import React, { useRef, useEffect } from 'react';
import { useChatStore } from '../../store/chatStore';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';
import EmptyState from '../common/EmptyState';
import QueryInput from './QueryInput';
import { submitQuery } from '../../services/chatService';

export default function ChatWindow() {
  const {
    messages,
    isLoading,
    isLoadingSession,
    activeSessionId,
    addMessage,
    setLoading,
    addSessionHistory
  } = useChatStore();

  const scrollRef = useRef(null);

  // Auto-scroll to bottom on new message
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSendMessage = async (text) => {
    if (!text.trim() || isLoading) return;

    // 1. Add User Message
    addMessage({
      role: 'user',
      content: text
    });

    setLoading(true, 'retrieving');

    try {
      // 2. Call HALO Backend
      const responseData = await submitQuery(text, activeSessionId);

      // 3. Add Assistant Message
      addMessage({
        role: 'assistant',
        content: responseData.answer,
        response: responseData
      });

      // 4. Update Session in History
      addSessionHistory({
        session_id: activeSessionId,
        title: text.slice(0, 40) + (text.length > 40 ? '...' : ''),
        timestamp: Date.now()
      });
    } catch (error) {
      console.error('HALO Query execution failed:', error);
      addMessage({
        role: 'assistant',
        content: 'Unable to reach HALO backend. Please check that FastAPI is running on port 8000.',
        response: {
          is_authoritative: false,
          fail_closed: true,
          answer: 'Unable to connect to the legal research server. Verify network connection and backend status.',
          confidence_score: 0.0,
          claims: [],
          retrieved_passages: []
        }
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        flex: 1,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'var(--surface-bg)',
        overflow: 'hidden',
        position: 'relative'
      }}
    >
      {/* Scrollable Message Area */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px 24px 16px',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {isLoadingSession ? (
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px'
            }}
          >
            <span style={{ fontSize: '28px', color: 'var(--brand-accent)' }}>⚖</span>
            <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
              Restoring legal research session transcript...
            </span>
          </div>
        ) : messages.length === 0 ? (
          <EmptyState onSelectQuery={handleSendMessage} />
        ) : (
          <div
            style={{
              width: '100%',
              maxWidth: '880px',
              margin: '0 auto',
              display: 'flex',
              flexDirection: 'column'
            }}
          >
            {messages.map((msg, idx) => (
              <MessageBubble key={msg.id || idx} message={msg} />
            ))}

            {isLoading && (
              <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 'var(--space-md)' }}>
                <TypingIndicator />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input Bar */}
      <QueryInput onSendMessage={handleSendMessage} disabled={isLoading} />
    </div>
  );
}
