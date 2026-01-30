import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, Result, Button } from 'antd';
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
import AIEffectReportPage from './pages/AIEffectReportPage';
import LoginPage from './pages/LoginPage';
import ProfilePage from './pages/ProfilePage';
import MainLayout from './components/MainLayout';
import RequireAuth from './components/RequireAuth';
import RequireRole from './components/RequireRole';
import usePermission from './hooks/usePermission';
import './App.css';

const HomeRedirect = () => {
  const { isAdmin, isManager, isExpert } = usePermission();
  if (isAdmin) {
    return <Navigate to="/tasks" replace />;
  }
  if (isManager && isExpert) {
    return <Navigate to="/tasks" replace />;
  }
  if (isManager) {
    return <Navigate to="/tasks/my-tasks" replace />;
  }
  if (isExpert) {
    return <Navigate to="/tasks/my-evaluations" replace />;
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
            <Route path="/tasks" element={<TaskListPage />} />
            <Route
              path="/tasks/my-tasks"
              element={(
                <RequireRole roles={['manager']}>
                  <TaskListPage />
                </RequireRole>
              )}
            />
            <Route
              path="/tasks/my-evaluations"
              element={(
                <RequireRole roles={['expert']}>
                  <TaskListPage />
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
                <RequireRole roles={['admin', 'manager']}>
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
                  <AIEffectReportPage />
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
              element={(
                <Navigate to="/users" replace />
              )}
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
