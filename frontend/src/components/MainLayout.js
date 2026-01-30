import React, { useEffect, useMemo, useState } from 'react';
import { Avatar, Badge, Dropdown, Layout, Menu, Space, Typography } from 'antd';
import {
  BellOutlined,
  FileTextOutlined,
  SettingOutlined,
  UserOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import usePermission from '../hooks/usePermission';
import useNotification from '../hooks/useNotification';
import './MainLayout.css';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const roleLabels = {
  admin: '管理员',
  manager: '项目经理',
  expert: '专家',
};

const MainLayout = () => {
  const { user, logout } = useAuth();
  const { roles, isAdmin, isManager, isExpert, hasAnyRole } = usePermission();
  const { unread, refreshUnread } = useNotification() || {};
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (refreshUnread) {
      refreshUnread();
    }
  }, [refreshUnread, location.pathname]);

  const taskMenuItem = useMemo(() => {
    if (isAdmin) {
      return { key: '/tasks', label: '任务管理', icon: <FileTextOutlined /> };
    }
    if (isManager && isExpert) {
      return { key: '/tasks', label: '任务管理', icon: <FileTextOutlined /> };
    }
    if (isManager) {
      return { key: '/tasks/my-tasks', label: '任务管理', icon: <FileTextOutlined /> };
    }
    if (isExpert) {
      return { key: '/tasks/my-evaluations', label: '任务管理', icon: <FileTextOutlined /> };
    }
    return null;
  }, [isAdmin, isManager, isExpert]);

  const menuItems = useMemo(() => {
    const items = [];

    if (taskMenuItem) {
      items.push(taskMenuItem);
    }

    if (hasAnyRole(['admin', 'manager'])) {
      const configChildren = [];
      if (isAdmin) {
        configChildren.push({ key: '/config/system-list', label: '系统清单' });
        configChildren.push({ key: '/config/cosmic', label: '规则管理' });
        configChildren.push({ key: '/users', label: '用户管理' });
      }
      if (isManager) {
        configChildren.push({ key: '/knowledge', label: '知识库管理' });
      }
      if (configChildren.length) {
        items.push({
          key: 'config-group',
          label: '配置管理',
          icon: <SettingOutlined />,
          children: configChildren,
        });
      }
    }

    if (hasAnyRole(['admin', 'manager', 'expert'])) {
      items.push({
        key: '/reports/ai-effect',
        label: '效果统计',
        icon: <BarChartOutlined />,
      });
    }

    items.push({
      key: 'personal-group',
      label: '个人',
      icon: <UserOutlined />,
      children: [
        {
          key: '/notifications',
          label: '消息通知',
          icon: (
            <Badge count={unread} size="small" offset={[8, 0]}>
              <BellOutlined />
            </Badge>
          ),
        },
        { key: '/profile', label: '个人中心' },
      ],
    });

    return items;
  }, [taskMenuItem, hasAnyRole, isAdmin, isManager, unread]);

  const selectedKey = useMemo(() => {
    if (location.pathname.startsWith('/tasks')) {
      return taskMenuItem?.key || '/tasks';
    }
    return location.pathname;
  }, [location.pathname, taskMenuItem]);

  const handleMenuClick = ({ key }) => {
    navigate(key);
  };

  const roleTags = roles.length
    ? roles.map((role) => roleLabels[role] || role).join(' / ')
    : '未分配';

  const userMenu = {
    items: [
      {
        key: 'profile',
        label: '个人中心',
        onClick: () => navigate('/profile'),
      },
      {
        key: 'logout',
        label: '退出登录',
        onClick: () => {
          logout();
          navigate('/login');
        },
      },
    ],
  };

  return (
    <Layout className="app-layout">
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={220}
        className="app-sider"
      >
        <div className="app-logo">
          <div className="app-logo-mark">REQ</div>
          {!collapsed && <div className="app-logo-text">需求评估系统</div>}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          items={menuItems}
          selectedKeys={[selectedKey]}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <div className="app-header-left">
            <Text className="app-header-title">业务需求工作量评估</Text>
          </div>
          <div className="app-header-right">
            <Space size={16} align="center">
              <span className="app-role-badge">{roleTags}</span>
              <Badge count={unread} size="small">
                <BellOutlined className="app-header-icon" onClick={() => navigate('/notifications')} />
              </Badge>
              <Dropdown menu={userMenu} placement="bottomRight">
                <Space className="app-user" align="center">
                  <Avatar size="small" src={user?.avatar} icon={<UserOutlined />} />
                  <Text>{user?.displayName || user?.username || '用户'}</Text>
                </Space>
              </Dropdown>
            </Space>
          </div>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
