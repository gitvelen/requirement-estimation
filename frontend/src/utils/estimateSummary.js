export const toFiniteEstimateNumber = (value) => {
  if (value === undefined || value === null || value === '') {
    return null;
  }
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
};

export const sumEstimateValues = (rows = [], resolveValue = (row) => row) => {
  const total = (Array.isArray(rows) ? rows : []).reduce((sum, row) => {
    const value = toFiniteEstimateNumber(resolveValue(row));
    return value === null ? sum : sum + value;
  }, 0);
  return Math.round(total * 100) / 100;
};

export const formatEstimateTotal = (value) => {
  const num = toFiniteEstimateNumber(value) ?? 0;
  return String(Math.round(num * 100) / 100);
};
