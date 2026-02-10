import React, { useMemo, useState } from 'react';
import { Button, Space, Tooltip, Typography } from 'antd';

const { Text } = Typography;

const splitText = (value, limit) => {
  const text = String(value || '');
  if (text.length <= limit) {
    return { shortText: text, needsExpand: false };
  }
  return {
    shortText: `${text.slice(0, limit)}...`,
    needsExpand: true,
  };
};

const ExpandableText = ({ value, limit = 80, empty = '-', withTooltip = false }) => {
  const [expanded, setExpanded] = useState(false);

  const resolved = useMemo(() => splitText(value, limit), [value, limit]);
  const raw = String(value || '').trim();

  if (!raw) {
    return <Text type="secondary">{empty}</Text>;
  }

  if (!resolved.needsExpand) {
    return <Text style={{ whiteSpace: 'pre-wrap' }}>{raw}</Text>;
  }

  const currentText = expanded ? raw : resolved.shortText;
  const textNode = <Text style={{ whiteSpace: 'pre-wrap' }}>{currentText}</Text>;

  return (
    <Space direction="vertical" size={0}>
      {withTooltip ? <Tooltip title={raw}>{textNode}</Tooltip> : textNode}
      <Button type="link" size="small" style={{ padding: 0, height: 'auto' }} onClick={() => setExpanded((prev) => !prev)}>
        {expanded ? '收起' : '展开'}
      </Button>
    </Space>
  );
};

export default ExpandableText;
