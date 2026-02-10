import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Avatar, Badge, Dropdown, Layout, Menu, Space, Typography } from 'antd';
import {
  BellOutlined,
  FileTextOutlined,
  SettingOutlined,
  UserOutlined,
  DashboardOutlined,
  ApartmentOutlined,
  DownOutlined,
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
  viewer: '查看者',
};

const MainLayout = () => {
  const { user, logout } = useAuth();
  const { roles, activeRole, setActiveRole, isAdmin, isManager, isExpert, isViewer } = usePermission();
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
    if (isAdmin || isManager || isExpert || isViewer) {
      return { key: '/tasks', label: '任务管理', icon: <FileTextOutlined /> };
    }
    return null;
  }, [isAdmin, isManager, isExpert, isViewer]);

  const menuItems = useMemo(() => {
    const items = [];

    if (taskMenuItem) {
      items.push(taskMenuItem);
    }

    // 项目经理：系统画像菜单（知识导入 + 信息看板）
    if (isManager) {
      items.push({
        key: 'system-profile-group',
        label: '系统画像',
        icon: <ApartmentOutlined />,
        children: [
          { key: '/system-profiles/import', label: '知识导入' },
          { key: '/system-profiles/board', label: '信息看板' },
        ],
      });
    }

    // 管理员：配置管理菜单（系统清单 + 规则管理 + 用户管理）
    if (isAdmin) {
      items.push({
        key: 'config-group',
        label: '配置管理',
        icon: <SettingOutlined />,
        children: [
          { key: '/config/system-list', label: '系统清单' },
          { key: '/config/cosmic', label: '规则管理' },
          { key: '/users', label: '用户管理' },
        ],
      });
    }

    if (isAdmin || isManager || isExpert || isViewer) {
      items.push({
        key: '/dashboard',
        label: '效能看板',
        icon: <DashboardOutlined />,
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
  }, [taskMenuItem, isAdmin, isManager, isExpert, isViewer, unread]);

  const selectedKey = useMemo(() => {
    if (location.pathname.startsWith('/tasks')) {
      return taskMenuItem?.key || '/tasks';
    }
    if (location.pathname.startsWith('/dashboard')) {
      return '/dashboard';
    }
    if (location.pathname.startsWith('/system-profiles')) {
      if (location.pathname.startsWith('/system-profiles/import')) {
        return '/system-profiles/import';
      }
      return '/system-profiles/board';
    }
    return location.pathname;
  }, [location.pathname, taskMenuItem]);

  const handleMenuClick = ({ key }) => {
    const path = String(key || '');
    if (path.startsWith('/system-profiles')) {
      navigate(`${path}${location.search || ''}`);
      return;
    }
    navigate(path);
  };

  const handleSwitchRole = useCallback((nextRole) => {
    const normalized = String(nextRole || '').trim();
    if (!normalized || normalized === activeRole) {
      return;
    }
    setActiveRole(normalized);
    const targetPath = normalized === 'admin' || normalized === 'viewer' ? '/dashboard' : '/tasks';
    navigate(targetPath, { replace: true });
  }, [activeRole, navigate, setActiveRole]);

  const roleMenu = useMemo(() => ({
    items: (roles || []).map((role) => ({
      key: role,
      label: roleLabels[role] || role,
      disabled: role === activeRole,
      onClick: () => handleSwitchRole(role),
    })),
  }), [roles, activeRole, handleSwitchRole]);

  const activeRoleLabel = roleLabels[activeRole] || activeRole || '未分配';

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
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} width={220} className="app-sider">
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
              <Dropdown menu={roleMenu} placement="bottomRight" disabled={(roles || []).length <= 1}>
                <Space className="app-role-badge" align="center" style={{ cursor: (roles || []).length <= 1 ? 'default' : 'pointer' }}>
                  <span>{activeRoleLabel}</span>
                  {(roles || []).length > 1 && <DownOutlined style={{ fontSize: 12 }} />}
                </Space>
              </Dropdown>
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
