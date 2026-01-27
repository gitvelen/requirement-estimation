/**
 * 前端安全工具函数
 * 防止XSS攻击
 */

import DOMPurify from 'dompurify';

/**
 * 清理HTML内容，防止XSS攻击
 * @param {string} dirty - 未清理的HTML字符串
 * @param {Object} options - DOMPurify配置选项
 * @returns {string} 清理后的安全HTML字符串
 */
export const sanitizeHTML = (dirty, options = {}) => {
  if (typeof dirty !== 'string') {
    return '';
  }

  // 默认配置：严格模式，禁止所有标签和属性
  const defaultOptions = {
    ALLOWED_TAGS: [], // 默认不允许任何HTML标签
    ALLOWED_ATTR: [], // 默认不允许任何属性
    KEEP_CONTENT: true, // 保留文本内容
    ...options
  };

  return DOMPurify.sanitize(dirty, defaultOptions);
};

/**
 * 转义HTML特殊字符
 * @param {string} str - 需要转义的字符串
 * @returns {string} 转义后的字符串
 */
export const escapeHTML = (str) => {
  if (typeof str !== 'string') {
    return '';
  }

  const htmlEntities = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
    '/': '&#x2F;'
  };

  return str.replace(/[&<>"'/]/g, (char) => htmlEntities[char]);
};

/**
 * 验证URL是否安全
 * @param {string} url - 需要验证的URL
 * @returns {boolean} URL是否安全
 */
export const isValidURL = (url) => {
  if (typeof url !== 'string') {
    return false;
  }

  try {
    const parsed = new URL(url);
    // 只允许http和https协议
    return ['http:', 'https:'].includes(parsed.protocol);
  } catch {
    return false;
  }
};

/**
 * 验证文件名是否安全
 * @param {string} filename - 文件名
 * @returns {boolean} 文件名是否安全
 */
export const isValidFilename = (filename) => {
  if (typeof filename !== 'string') {
    return false;
  }

  // 检查路径遍历攻击
  if (filename.includes('..') || filename.includes('/') || filename.includes('\\')) {
    return false;
  }

  // 检查是否包含非法字符
  const invalidChars = /[<>:"|?*\x00-\x1F]/;
  if (invalidChars.test(filename)) {
    return false;
  }

  return filename.length > 0 && filename.length < 255;
};

export default {
  sanitizeHTML,
  escapeHTML,
  isValidURL,
  isValidFilename
};
