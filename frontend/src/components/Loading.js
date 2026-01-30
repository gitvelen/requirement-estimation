import React from 'react';
import { Spin } from 'antd';

const Loading = ({ tip = '加载中...', size = 'large', fullScreen = false, height }) => {
  const wrapperStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
  };
  const placeholderStyle = {
    minHeight: fullScreen ? '60vh' : height || '120px',
    width: '100%',
  };
  return (
    <div style={wrapperStyle}>
      <Spin size={size} tip={tip} spinning>
        <div style={placeholderStyle} />
      </Spin>
    </div>
  );
};

export default Loading;
