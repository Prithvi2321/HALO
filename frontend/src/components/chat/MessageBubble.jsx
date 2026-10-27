import React from 'react';
import AnswerBlock from './AnswerBlock';

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div
        className="animate-slide-up"
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          marginBottom: 'var(--space-md)'
        }}
      >
        <div
          style={{
            maxWidth: '640px',
            padding: '12px 18px',
            backgroundColor: 'var(--brand-primary)',
            border: '1px solid var(--border-strong)',
            borderRadius: 'var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg)',
            color: 'var(--text-primary)',
            fontSize: 'var(--text-base)',
            lineHeight: '1.5',
            boxShadow: 'var(--shadow-sm)'
          }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  // Assistant Response Block
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'flex-start',
        marginBottom: 'var(--space-lg)'
      }}
    >
      <AnswerBlock response={message.response || { answer: message.content }} />
    </div>
  );
}
