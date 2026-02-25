import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ConfigProvider, Result, Button, message } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import UploadPage from './pages/UploadPage';
import TaskListPage from './pages/TaskListPage';
import ReportPage from './pages/ReportPage';
import EditPage from './pages/EditPage';
import EvaluationPage from './pages/EvaluationPage';
import CosmicConfigPage from './pages/CosmicConfigPage';
import SystemListConfigPage from './pages/SystemListConfigPage';
import KnowledgePage from './pages/KnowledgePage';
import UserManagementPage from './pages/UserManagementPage';
import NotificationPage from './pages/NotificationPage';
import LoginPage from './pages/LoginPage';
import ProfilePage from './pages/ProfilePage';
import DashboardRankingsPage from './pages/DashboardRankingsPage';
import DashboardReportsPage from './pages/DashboardReportsPage';
import SystemProfileImportPage from './pages/SystemProfileImportPage';
import SystemProfileBoardPage from './pages/SystemProfileBoardPage';
import MainLayout from './components/MainLayout';
import RequireAuth from './components/RequireAuth';
import RequireRole from './components/RequireRole';
import usePermission from './hooks/usePermission';
import './App.css';

const AI_EFFECT_OFFLINE_TIP_STORAGE_KEY = 'ai_effect_report_offline_tip_shown_v22';

const showAIEffectOfflineTipOnce = () => {
  try {
    if (sessionStorage.getItem(AI_EFFECT_OFFLINE_TIP_STORAGE_KEY) === '1') {
      return;
    }
    sessionStorage.setItem(AI_EFFECT_OFFLINE_TIP_STORAGE_KEY, '1');
  } catch (error) {
    // ignore storage exceptions (privacy mode, disabled storage, etc.)
  }
  message.info('AI效果报告已下线');
};

const HomeRedirect = () => {
  const { activeRole, hasAnyRole } = usePermission();

  if (activeRole === 'admin') {
    return <Navigate to="/dashboard/reports" replace />;
  }
  if (activeRole === 'manager') {
    return <Navigate to="/tasks/ongoing" replace />;
  }
  if (activeRole === 'expert') {
    return <Navigate to="/tasks/ongoing" replace />;
  }
  if (activeRole === 'viewer') {
    return <Navigate to="/dashboard/reports" replace />;
  }
  if (hasAnyRole(['admin'])) {
    return <Navigate to="/dashboard/reports" replace />;
  }
  if (hasAnyRole(['manager', 'expert'])) {
    return <Navigate to="/tasks/ongoing" replace />;
  }
  if (hasAnyRole(['viewer'])) {
    return <Navigate to="/dashboard/reports" replace />;
  }
  return <Navigate to="/profile" replace />;
};

const NotFound = () => (
  <Result
    status="404"
    title="页面不存在"
    subTitle="您访问的页面不存在"
    extra={(
      <Button type="primary" href="/">
        返回首页
      </Button>
    )}
  />
);

const LegacyAIEffectRedirect = () => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    showAIEffectOfflineTipOnce();
    navigate(`/dashboard/reports${location.search || ''}`, { replace: true });
  }, [location.search, navigate]);

  return null;
};

const LegacyDashboardRedirect = () => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(location.search || '');
    const page = String(params.get('page') || '').trim().toLowerCase();
    params.delete('page');

    if (page === 'ai') {
      showAIEffectOfflineTipOnce();
    }

    const target = page === 'rankings' ? '/dashboard/rankings' : '/dashboard/reports';
    const search = params.toString();
    navigate(`${target}${search ? `?${search}` : ''}`, { replace: true });
  }, [location.search, navigate]);

  return null;
};

const LegacyTasksRedirect = () => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(location.search || '');
    const tab = String(params.get('tab') || '').trim().toLowerCase();
    params.delete('tab');

    const target = tab === 'completed' ? '/tasks/completed' : '/tasks/ongoing';
    const search = params.toString();
    navigate(`${target}${search ? `?${search}` : ''}`, { replace: true });
  }, [location.search, navigate]);

  return null;
};

const SystemProfilesRedirect = () => {
  const location = useLocation();
  return <Navigate to={`/system-profiles/board${location.search || ''}`} replace />;
};

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={(
              <RequireAuth>
                <MainLayout />
              </RequireAuth>
            )}
          >
            <Route path="/" element={<HomeRedirect />} />
            <Route
              path="/dashboard"
              element={(
                <RequireRole roles={['admin', 'manager', 'expert', 'viewer']}>
                  <LegacyDashboardRedirect />
                </RequireRole>
              )}
            />
            <Route
              path="/tasks"
              element={(
                <RequireRole roles={['admin', 'manager', 'expert', 'viewer']}>
                  <LegacyTasksRedirect />
                </RequireRole>
              )}
            />
            <Route
              path="/tasks/my-tasks"
              element={(
                <RequireRole roles={['manager']}>
                  <Navigate to="/tasks/ongoing" replace />
                </RequireRole>
              )}
            />
            <Route
              path="/tasks/my-evaluations"
              element={(
                <RequireRole roles={['expert']}>
                  <Navigate to="/tasks/ongoing" replace />
                </RequireRole>
              )}
            />
            <Route
              path="/tasks/ongoing"
              element={(
                <RequireRole roles={['admin', 'manager', 'expert', 'viewer']}>
                  <TaskListPage defaultTab="ongoing" />
                </RequireRole>
              )}
            />
            <Route
              path="/tasks/completed"
              element={(
                <RequireRole roles={['admin', 'manager', 'expert', 'viewer']}>
                  <TaskListPage defaultTab="completed" />
                </RequireRole>
              )}
            />
            <Route
              path="/upload"
              element={(
                <RequireRole roles={['manager']}>
                  <UploadPage />
                </RequireRole>
              )}
            />
            <Route
              path="/report/:taskId"
              element={(
                <RequireRole roles={['admin', 'manager', 'expert']}>
                  <ReportPage />
                </RequireRole>
              )}
            />
            <Route
              path="/edit/:taskId"
              element={(
                <RequireRole roles={['manager']}>
                  <EditPage />
                </RequireRole>
              )}
            />
            <Route
              path="/evaluate/:taskId"
              element={(
                <RequireRole roles={['expert']}>
                  <EvaluationPage />
                </RequireRole>
              )}
            />
            <Route
              path="/system-profiles"
              element={(
                <RequireRole roles={['manager']}>
                  <SystemProfilesRedirect />
                </RequireRole>
              )}
            />
            <Route
              path="/system-profiles/import"
              element={(
                <RequireRole roles={['manager']}>
                  <SystemProfileImportPage />
                </RequireRole>
              )}
            />
            <Route
              path="/system-profiles/board"
              element={(
                <RequireRole roles={['manager']}>
                  <SystemProfileBoardPage />
                </RequireRole>
              )}
            />
            <Route
              path="/knowledge"
              element={(
                <RequireRole roles={['manager']}>
                  <KnowledgePage />
                </RequireRole>
              )}
            />
            <Route
              path="/users"
              element={(
                <RequireRole roles={['admin']}>
                  <UserManagementPage />
                </RequireRole>
              )}
            />
            <Route path="/notifications" element={<NotificationPage />} />
            <Route
              path="/reports/ai-effect"
              element={(
                <RequireRole roles={['admin', 'manager', 'expert']}>
                  <LegacyAIEffectRedirect />
                </RequireRole>
              )}
            />
            <Route
              path="/dashboard/rankings"
              element={(
                <RequireRole roles={['admin', 'manager', 'expert', 'viewer']}>
                  <DashboardRankingsPage />
                </RequireRole>
              )}
            />
            <Route
              path="/dashboard/reports"
              element={(
                <RequireRole roles={['admin', 'manager', 'expert', 'viewer']}>
                  <DashboardReportsPage />
                </RequireRole>
              )}
            />
            <Route
              path="/config/subsystem"
              element={<Navigate to="/config/system-list" replace />}
            />
            <Route
              path="/config/cosmic"
              element={(
                <RequireRole roles={['admin']}>
                  <CosmicConfigPage />
                </RequireRole>
              )}
            />
            <Route
              path="/config/mainsystem"
              element={<Navigate to="/config/system-list" replace />}
            />
            <Route
              path="/config/system-list"
              element={(
                <RequireRole roles={['admin']}>
                  <SystemListConfigPage />
                </RequireRole>
              )}
            />
            <Route
              path="/config/experts"
              element={<Navigate to="/users" replace />}
            />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </Router>
    </ConfigProvider>
  );
}

export default App;
