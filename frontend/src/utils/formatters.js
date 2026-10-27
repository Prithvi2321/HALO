/**
 * Formatting utilities for HALO Nyaya Sahayak
 */

export function formatConfidence(score) {
  if (typeof score !== 'number') return '91%';
  const pct = Math.round(score <= 1.0 ? score * 100 : score);
  return `${pct}%`;
}

export function getConfidenceCircles(score) {
  const norm = typeof score === 'number' ? (score <= 1.0 ? score : score / 100) : 0.91;
  const filled = Math.min(5, Math.max(1, Math.round(norm * 5)));
  return {
    filled,
    total: 5,
    string: '●'.repeat(filled) + '○'.repeat(5 - filled)
  };
}

export function formatDate(timestamp) {
  if (!timestamp) return 'Today';
  const date = new Date(typeof timestamp === 'number' && timestamp < 1e11 ? timestamp * 1000 : timestamp);
  const now = new Date();
  const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
}

export function truncate(text, maxLength = 80) {
  if (!text) return '';
  return text.length > maxLength ? text.slice(0, maxLength) + '...' : text;
}
