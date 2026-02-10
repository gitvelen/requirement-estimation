const pad = (value) => String(value).padStart(2, '0');

const toLocalIso = (date) => {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    return '';
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
};

export const formatDateTime = (value) => {
  if (!value) {
    return '-';
  }
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
};

const normalizeDate = (value) => {
  if (!value) {
    return null;
  }
  if (typeof value.toDate === 'function') {
    return value.toDate();
  }
  if (value instanceof Date) {
    return value;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed;
};

export const toIsoStartOfDay = (value) => {
  const date = normalizeDate(value);
  if (!date) {
    return '';
  }
  const next = new Date(date);
  next.setHours(0, 0, 0, 0);
  return toLocalIso(next);
};

export const toIsoEndOfDay = (value) => {
  const date = normalizeDate(value);
  if (!date) {
    return '';
  }
  const next = new Date(date);
  next.setHours(23, 59, 59, 0);
  return toLocalIso(next);
};
