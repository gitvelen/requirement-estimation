import React from 'react';
import { Button, Result } from 'antd';
import { useNavigate } from 'react-router-dom';
import usePermission from '../hooks/usePermission';

const RequireRole = ({ roles, children }) => {
  const navigate = useNavigate();
  const { activeRole } = usePermission();

  if (roles && roles.length && !roles.includes(activeRole)) {
    return (
      <Result
        status="403"
        title="没有权限"
        subTitle="当前账号无权访问此页面"
        extra={(
          <Button type="primary" onClick={() => navigate(-1)}>
            返回
          </Button>
        )}
      />
    );
  }

  return children;
};

export default RequireRole;
