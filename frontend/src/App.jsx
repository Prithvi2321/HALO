import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import { useChatStore } from './store/chatStore';
import { fetchStats } from './services/chatService';

export default function App() {
  const { activeSessionId, createNewSession, setCorpusStats } = useChatStore();

  useEffect(() => {
    if (!activeSessionId) {
      createNewSession();
    }

    async function loadStats() {
      try {
        const stats = await fetchStats();
        if (stats) setCorpusStats(stats);
      } catch (err) {
        console.warn('Backend stats not yet available, using defaults.');
      }
    }
    loadStats();
  }, [activeSessionId, createNewSession, setCorpusStats]);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />} />
        <Route path="/history" element={<Layout />} />
      </Routes>
    </Router>
  );
}
