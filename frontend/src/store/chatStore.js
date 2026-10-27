import { create } from 'zustand';
import { fetchSessionMessages, deleteSessionHistory } from '../services/historyService';

export const useChatStore = create((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: [],
  isLoading: false,
  isLoadingSession: false,
  loadingStage: null, // 'retrieving' | 'verifying' | 'anchoring'
  evidencePanelOpen: false,
  activePassage: null,
  corpusStats: {
    total_passages: 12223,
    acts_count: 470,
    judgments_count: 854
  },

  setActiveSessionId: (sessionId) => {
    set({ activeSessionId: sessionId });
  },

  createNewSession: () => {
    const newId = `ses_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    set({
      activeSessionId: newId,
      messages: [],
      evidencePanelOpen: false,
      activePassage: null
    });
    return newId;
  },

  loadSession: async (sessionId) => {
    if (!sessionId || sessionId === get().activeSessionId) return;
    set({ isLoadingSession: true, activeSessionId: sessionId, evidencePanelOpen: false, activePassage: null });
    try {
      const messages = await fetchSessionMessages(sessionId);
      set({ messages });
    } catch (err) {
      console.error('Failed to restore session:', err);
    } finally {
      set({ isLoadingSession: false });
    }
  },

  removeSession: async (sessionId) => {
    if (!sessionId) return;
    try {
      await deleteSessionHistory(sessionId);
      const remaining = get().sessions.filter((s) => s.session_id !== sessionId);
      set({ sessions: remaining });
      if (get().activeSessionId === sessionId) {
        get().createNewSession();
      }
    } catch (err) {
      console.error('Failed to remove session:', err);
    }
  },

  setMessages: (messages) => set({ messages }),

  addMessage: (message) => {
    set((state) => ({
      messages: [...state.messages, { ...message, id: message.id || `msg_${Date.now()}` }]
    }));
  },

  setLoading: (isLoading, loadingStage = null) => {
    set({ isLoading, loadingStage });
  },

  setLoadingStage: (stage) => set({ loadingStage: stage }),

  openEvidencePanel: (passage) => {
    set({
      evidencePanelOpen: true,
      activePassage: passage
    });
  },

  closeEvidencePanel: () => {
    set({
      evidencePanelOpen: false,
      activePassage: null
    });
  },

  setCorpusStats: (stats) => {
    set((state) => ({
      corpusStats: { ...state.corpusStats, ...stats }
    }));
  },

  setSessions: (sessions) => set({ sessions }),

  addSessionHistory: (session) => {
    set((state) => {
      const exists = state.sessions.some((s) => s.session_id === session.session_id);
      if (exists) {
        return {
          sessions: state.sessions.map((s) =>
            s.session_id === session.session_id ? { ...s, ...session } : s
          )
        };
      }
      return { sessions: [session, ...state.sessions] };
    });
  }
}));
