import React, { useMemo } from 'react';
import { Card, Typography } from 'antd';

const { Text } = Typography;

const DIRECTION_LABELS = {
  outbound: '→',
  out: '→',
  inbound: '←',
  in: '←',
  bidirectional: '⇄',
};

const normalizeString = (value) => String(value ?? '').trim();

const normalizeIntegrationPoints = (value) => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => ({
    peer_system: normalizeString(item?.peer_system),
    protocol: normalizeString(item?.protocol),
    direction: normalizeString(item?.direction).toLowerCase(),
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

const normalizeRiskRows = (value) => {
  if (Array.isArray(value)) {
    return value.map((item) => ({ risk: normalizeString(item?.risk ?? item) })).filter((item) => item.risk);
  }
  const text = normalizeString(value);
  return text ? [{ risk: text }] : [];
};

const normalizePerformanceRows = (value) => {
  if (Array.isArray(value)) {
    return value.map((item) => ({
      metric: normalizeString(item?.metric ?? item?.key),
      value: normalizeString(item?.value),
    }));
  }
  if (!value || typeof value !== 'object') {
    return [];
  }
  return Object.entries(value).map(([metric, metricValue]) => ({
    metric: normalizeString(metric),
    value: normalizeString(metricValue),
  }));
};

const renderEmpty = () => <Text type="secondary">—</Text>;

const SimpleTable = ({ headers, rows }) => {
  if (!rows.length) {
    return renderEmpty();
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {headers.map((header) => (
              <th
                key={header.key}
                style={{
                  borderBottom: '1px solid #f0f0f0',
                  padding: '6px 8px',
                  textAlign: 'left',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                }}
              >
                {header.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`row-${rowIndex}`}>
              {headers.map((header) => (
                <td
                  key={`${rowIndex}-${header.key}`}
                  style={{ borderBottom: '1px solid #f5f5f5', padding: '6px 8px', verticalAlign: 'top' }}
                >
                  {row[header.key] || <Text type="secondary">—</Text>}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const StructuredFieldPreview = ({ title, kind, value }) => {
  const preview = useMemo(() => {
    if (kind === 'integration_points') {
      return {
        headers: [
          { key: 'peer_system', label: '对端系统' },
          { key: 'protocol', label: '协议' },
          { key: 'direction', label: '方向' },
          { key: 'description', label: '集成说明' },
        ],
        rows: normalizeIntegrationPoints(value).map((item) => ({
          ...item,
          direction: DIRECTION_LABELS[item.direction] || '未知方向',
        })),
      };
    }

    if (kind === 'key_constraints') {
      return {
        headers: [
          { key: 'category', label: '约束类型' },
          { key: 'description', label: '内容' },
        ],
        rows: normalizeKeyConstraints(value),
      };
    }

    if (kind === 'known_risks') {
      return {
        headers: [{ key: 'risk', label: '风险项' }],
        rows: normalizeRiskRows(value),
      };
    }

    if (kind === 'performance_profile') {
      return {
        headers: [
          { key: 'metric', label: '指标' },
          { key: 'value', label: '数值' },
        ],
        rows: normalizePerformanceRows(value),
      };
    }

    return { headers: [], rows: [] };
  }, [kind, value]);

  return (
    <Card size="small" title={title || undefined}>
      <SimpleTable headers={preview.headers} rows={preview.rows} />
    </Card>
  );
};

export default StructuredFieldPreview;
