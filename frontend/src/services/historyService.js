import api from './api';

export async function fetchHistory() {
  try {
    const response = await api.get('/api/history');
    return response.data.sessions || [];
  } catch (error) {
    console.warn('History service unreachable:', error);
    return [];
  }
}

export async function fetchSessionMessages(sessionId) {
  try {
    const response = await api.get(`/api/history/${encodeURIComponent(sessionId)}`);
    return response.data.messages || [];
  } catch (error) {
    console.error(`Failed to fetch session messages for ${sessionId}:`, error);
    return [];
  }
}

export async function deleteSessionHistory(sessionId) {
  try {
    const response = await api.delete(`/api/history/${encodeURIComponent(sessionId)}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to delete session ${sessionId}:`, error);
    return null;
  }
}
