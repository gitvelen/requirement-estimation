import React from 'react';
import { Tag } from 'antd';

const defaultStatusMap = {
  draft: { color: 'default', text: '草稿' },
  awaiting_assignment: { color: 'warning', text: '待分配' },
  evaluating: { color: 'processing', text: '评估中' },
  completed: { color: 'success', text: '已完成' },
  archived: { color: 'default', text: '已归档' },
  pending: { color: 'default', text: '待处理' },
  processing: { color: 'processing', text: '处理中' },
  failed: { color: 'error', text: '失败' },
  success: { color: 'success', text: '成功' },
  enabled: { color: 'success', text: '启用' },
  disabled: { color: 'default', text: '禁用' },
};

const StatusTag = ({ status, map, text, color }) => {
  const fromMap = (map && status && map[status]) || defaultStatusMap[status];
  const finalText = text || fromMap?.text || status || '-';
  const finalColor = color || fromMap?.color || 'default';
  return <Tag color={finalColor}>{finalText}</Tag>;
};

export default StatusTag;
