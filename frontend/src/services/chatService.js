import api from './api';

export async function submitQuery(query, sessionId) {
  const response = await api.post('/api/query', {
    query,
    session_id: sessionId
  });
  return response.data;
}

export async function fetchStats() {
  const response = await api.get('/api/stats');
  return response.data;
}
