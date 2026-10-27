/**
 * Citation Parser: Splits answer text and identifies [PAS_...] passage references
 */
export function parseCitationTokens(text) {
  if (!text) return [];

  // Match [PAS_...] or [PAS-...] or [SEC_...]
  const regex = /\[(PAS[-_][A-Za-z0-9_\-\.]+|SEC[-_][A-Za-z0-9_\-\.]+)\]/g;
  const tokens = [];
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      tokens.push({
        type: 'text',
        value: text.slice(lastIndex, match.index)
      });
    }

    tokens.push({
      type: 'citation',
      value: match[0],
      passageId: match[1]
    });

    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    tokens.push({
      type: 'text',
      value: text.slice(lastIndex)
    });
  }

  return tokens;
}

/**
 * Format a raw passage ID into a human-readable legal label
 */
export function formatCitationLabel(passageId) {
  if (!passageId) return 'Evidence';

  if (passageId.includes('SEC_')) {
    const secPart = passageId.split('SEC_')[1];
    const secNum = secPart.split('_')[0];
    const subPart = secPart.includes('SUB_') ? `(${secPart.split('SUB_')[1]})` : '';
    return `Sec. ${secNum}${subPart}`;
  }

  if (passageId.includes('SCH_')) {
    const schNum = passageId.split('SCH_')[1];
    return `Schedule ${schNum}`;
  }

  if (passageId.includes('JUD-SC')) {
    return 'SC Precedent';
  }

  if (passageId.includes('JUD-NCLAT')) {
    return 'NCLAT Ruling';
  }

  return passageId.replace('PAS_', '').replace('ACT_COMPANIES_2013_', '');
}
