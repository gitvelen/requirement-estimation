import React from 'react';
import { Button, Space, Typography } from 'antd';
import { LeftOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const PageHeader = ({ title, subtitle, extra, onBack }) => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
    marginBottom: 16,
  }}
  >
    <Space align="center">
      {onBack && (
        <Button type="text" icon={<LeftOutlined />} onClick={onBack}>
          返回
        </Button>
      )}
      <div>
        <Title level={4} style={{ margin: 0 }}>{title}</Title>
        {subtitle && <Text type="secondary">{subtitle}</Text>}
      </div>
    </Space>
    {extra && <div>{extra}</div>}
  </div>
);

export default PageHeader;
