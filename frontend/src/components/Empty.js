import React from 'react';
import { Empty as AntdEmpty } from 'antd';

const Empty = ({ description = '暂无数据', image }) => (
  <AntdEmpty
    description={description}
    image={image || AntdEmpty.PRESENTED_IMAGE_SIMPLE}
  />
);

export default Empty;
