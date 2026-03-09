import React, { useMemo } from 'react';
import { Space, Typography } from 'antd';
import { normalizeModuleStructureNodes } from '../../utils/systemProfileModuleStructure';

const { Text } = Typography;

const DIRECTION_LABELS = {
  outbound: '→',
  out: '→',
  inbound: '←',
  in: '←',
  bidirectional: '⇄',
};

const MARKER_COLORS = {
  '+': '#52c41a',
  '-': '#ff4d4f',
  '~': '#faad14',
};

const normalizeString = (value) => String(value ?? '').trim();

const normalizeStringList = (value) => {
  if (Array.isArray(value)) {
    return value.map((item) => normalizeString(item)).filter(Boolean);
  }
  const text = normalizeString(value);
  return text ? [text] : [];
};

const normalizeIntegrationPoints = (value) => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => ({
    peer_system: normalizeString(item?.peer_system),
    protocol: normalizeString(item?.protocol),
    direction: DIRECTION_LABELS[normalizeString(item?.direction).toLowerCase()] || '未知方向',
    description: normalizeString(item?.description ?? item?.name),
  }));
};

const normalizeKeyConstraints = (value) => {
  if (typeof value === 'string') {
    const text = normalizeString(value);
    return text ? [{ category: '通用', description: text }] : [];
  }
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => ({
    category: normalizeString(item?.category) || '通用',
    description: normalizeString(item?.description ?? item?.value),
  }));
};

const normalizePerformanceRows = (value) => {
  if (Array.isArray(value)) {
    return value.map((item) => ({ metric: normalizeString(item?.metric ?? item?.key), value: normalizeString(item?.value) }));
  }
  if (!value || typeof value !== 'object') {
    return [];
  }
  return Object.entries(value).map(([metric, metricValue]) => ({ metric: normalizeString(metric), value: normalizeString(metricValue) }));
};

const renderMarker = (marker) => (
  <span style={{ color: MARKER_COLORS[marker] || '#8c8c8c', fontWeight: 700, minWidth: 12, display: 'inline-block' }}>
    {marker}
  </span>
);

const renderTextDiff = (currentValue, suggestionValue) => (
  <div>
    <div style={{ display: 'grid', gap: 8, gridTemplateColumns: '1fr 1fr' }}>
      <div>
        <Text type="secondary">当前值</Text>
        <div style={{ marginTop: 4, padding: 8, borderRadius: 4, background: '#fff', minHeight: 44 }}>
          {normalizeString(currentValue) || <Text type="secondary">—</Text>}
        </div>
      </div>
      <div>
        <Text type="secondary">AI 建议</Text>
        <div style={{ marginTop: 4, padding: 8, borderRadius: 4, background: '#fff', minHeight: 44 }}>
          {normalizeString(suggestionValue) || <Text type="secondary">—</Text>}
        </div>
      </div>
    </div>
  </div>
);

const renderListDiff = (currentValue, suggestionValue) => {
  const currentItems = normalizeStringList(currentValue);
  const suggestionItems = normalizeStringList(suggestionValue);
  const commonItems = currentItems.filter((item) => suggestionItems.includes(item));
  const removedItems = currentItems.filter((item) => !suggestionItems.includes(item));
  const addedItems = suggestionItems.filter((item) => !currentItems.includes(item));
  const rows = [
    ...commonItems.map((item) => ({ marker: '~', value: item })),
    ...removedItems.map((item) => ({ marker: '-', value: item })),
    ...addedItems.map((item) => ({ marker: '+', value: item })),
  ];

  if (!rows.length) {
    return <Text type="secondary">—</Text>;
  }

  return (
    <div>
      <Text strong>列表变更</Text>
      <Space direction="vertical" size={6} style={{ width: '100%', marginTop: 8 }}>
        {rows.map((row, index) => (
          <div
            key={`list-diff-${index}`}
            style={{
              display: 'flex',
              gap: 8,
              alignItems: 'center',
              padding: '6px 8px',
              borderRadius: 4,
              background: row.marker === '+' ? '#f6ffed' : row.marker === '-' ? '#fff1f0' : '#fffbe6',
            }}
          >
            {renderMarker(row.marker)}
            <span>{row.value}</span>
          </div>
        ))}
      </Space>
    </div>
  );
};

const renderTableDiff = (title, headers, currentRows, suggestionRows) => {
  const currentMap = new Map(currentRows.map((row) => [JSON.stringify(row), row]));
  const suggestionMap = new Map(suggestionRows.map((row) => [JSON.stringify(row), row]));
  const rows = [
    ...currentRows.filter((row) => !suggestionMap.has(JSON.stringify(row))).map((row) => ({ marker: '-', row })),
    ...suggestionRows.filter((row) => !currentMap.has(JSON.stringify(row))).map((row) => ({ marker: '+', row })),
    ...suggestionRows.filter((row) => currentMap.has(JSON.stringify(row))).map((row) => ({ marker: '~', row })),
  ];

  if (!rows.length) {
    return <Text type="secondary">—</Text>;
  }

  return (
    <div>
      <Text strong>{title}</Text>
      <div style={{ overflowX: 'auto', marginTop: 8 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ borderBottom: '1px solid #f0f0f0', padding: '6px 8px', textAlign: 'left' }}>标记</th>
              {headers.map((header) => (
                <th key={header.key} style={{ borderBottom: '1px solid #f0f0f0', padding: '6px 8px', textAlign: 'left' }}>
                  {header.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((item, index) => (
              <tr key={`table-diff-${index}`}>
                <td style={{ borderBottom: '1px solid #f5f5f5', padding: '6px 8px' }}>{renderMarker(item.marker)}</td>
                {headers.map((header) => (
                  <td key={`${index}-${header.key}`} style={{ borderBottom: '1px solid #f5f5f5', padding: '6px 8px' }}>
                    {item.row[header.key] || <Text type="secondary">—</Text>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const buildTreeDiffRows = (currentNodes, suggestionNodes, depth = 1) => {
  const rows = [];
  const maxLength = Math.max(currentNodes.length, suggestionNodes.length);

  for (let index = 0; index < maxLength; index += 1) {
    const currentNode = currentNodes[index];
    const suggestionNode = suggestionNodes[index];

    if (!currentNode && suggestionNode) {
      rows.push({ marker: '+', label: suggestionNode.module_name, depth });
      rows.push(...buildTreeDiffRows([], suggestionNode.children || [], depth + 1));
      continue;
    }

    if (currentNode && !suggestionNode) {
      rows.push({ marker: '-', label: currentNode.module_name, depth });
      rows.push(...buildTreeDiffRows(currentNode.children || [], [], depth + 1));
      continue;
    }

    const changed = currentNode.module_name !== suggestionNode.module_name
      || normalizeString(currentNode.description) !== normalizeString(suggestionNode.description);
    rows.push({ marker: changed ? '~' : '~', label: suggestionNode.module_name, depth });
    rows.push(...buildTreeDiffRows(currentNode.children || [], suggestionNode.children || [], depth + 1));
  }

  return rows;
};

const renderTreeDiff = (currentValue, suggestionValue) => {
  const currentNodes = normalizeModuleStructureNodes(currentValue);
  const suggestionNodes = normalizeModuleStructureNodes(suggestionValue);
  const rows = buildTreeDiffRows(currentNodes, suggestionNodes);

  if (!rows.length) {
    return <Text type="secondary">—</Text>;
  }

  return (
    <div>
      <Text strong>树形变更</Text>
      <Space direction="vertical" size={6} style={{ width: '100%', marginTop: 8 }}>
        {rows.map((row, index) => (
          <div key={`tree-diff-${index}`} style={{ marginLeft: Math.max(0, row.depth - 1) * 20, display: 'flex', gap: 8, alignItems: 'center' }}>
            {renderMarker(row.marker)}
            <span>{row.label}</span>
          </div>
        ))}
      </Space>
    </div>
  );
};

const StructuredFieldDiffPreview = ({ kind, currentValue, suggestionValue }) => {
  const content = useMemo(() => {
    if (kind === 'text') {
      return renderTextDiff(currentValue, suggestionValue);
    }
    if (kind === 'list' || kind === 'known_risks') {
      return renderListDiff(currentValue, suggestionValue);
    }
    if (kind === 'integration_points') {
      return renderTableDiff(
        '表格变更',
        [
          { key: 'peer_system', label: '对端系统' },
          { key: 'protocol', label: '协议' },
          { key: 'direction', label: '方向' },
          { key: 'description', label: '集成说明' },
        ],
        normalizeIntegrationPoints(currentValue),
        normalizeIntegrationPoints(suggestionValue)
      );
    }
    if (kind === 'key_constraints') {
      return renderTableDiff(
        '表格变更',
        [
          { key: 'category', label: '约束类型' },
          { key: 'description', label: '内容' },
        ],
        normalizeKeyConstraints(currentValue),
        normalizeKeyConstraints(suggestionValue)
      );
    }
    if (kind === 'performance_profile') {
      return renderTableDiff(
        '表格变更',
        [
          { key: 'metric', label: '指标' },
          { key: 'value', label: '数值' },
        ],
        normalizePerformanceRows(currentValue),
        normalizePerformanceRows(suggestionValue)
      );
    }
    if (kind === 'module_structure') {
      return renderTreeDiff(currentValue, suggestionValue);
    }
    return renderTextDiff(currentValue, suggestionValue);
  }, [currentValue, kind, suggestionValue]);

  return <div>{content}</div>;
};

export default StructuredFieldDiffPreview;
