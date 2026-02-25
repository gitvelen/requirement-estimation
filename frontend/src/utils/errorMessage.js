const pickReadableDetail = (detail) => {
  if (!detail) {
    return '';
  }

  if (typeof detail === 'string') {
    return detail.trim();
  }

  if (Array.isArray(detail)) {
    for (const item of detail) {
      const text = pickReadableDetail(item);
      if (text) {
        return text;
      }
    }
    return '';
  }

  if (typeof detail === 'object') {
    const candidates = [
      detail.message,
      detail.msg,
      detail.detail,
      detail.reason,
      detail.error,
      detail.error_message,
    ];
    for (const candidate of candidates) {
      const text = pickReadableDetail(candidate);
      if (text) {
        return text;
      }
    }
  }

  return '';
};

export const extractErrorMessage = (error, fallback) => {
  const responseData = error?.response?.data;
  const responseText = pickReadableDetail(responseData);
  if (responseText) {
    return responseText;
  }

  const messageText = pickReadableDetail(error?.message);
  if (messageText) {
    return messageText;
  }

  return fallback;
};
