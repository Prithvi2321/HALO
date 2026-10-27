import React from 'react';
import Header from './Header';
import Sidebar from './Sidebar';
import ChatWindow from '../chat/ChatWindow';
import EvidencePanel from '../evidence/EvidencePanel';

export default function Layout() {
  return (
    <div
      style={{
        display: 'flex',
        width: '100vw',
        height: '100vh',
        backgroundColor: 'var(--surface-bg)',
        overflow: 'hidden'
      }}
    >
      {/* 1. Left Sidebar */}
      <Sidebar />

      {/* 2. Main Content Area */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
          position: 'relative'
        }}
      >
        <Header />
        <div style={{ flex: 1, display: 'flex', height: 'calc(100% - 60px)', overflow: 'hidden' }}>
          <ChatWindow />
          <EvidencePanel />
        </div>
      </div>
    </div>
  );
}
