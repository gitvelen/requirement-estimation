import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import UploadPage from './pages/UploadPage';
import TaskListPage from './pages/TaskListPage';
import ReportPage from './pages/ReportPage';
import EditPage from './pages/EditPage';
import SubsystemConfigPage from './pages/SubsystemConfigPage';
import CosmicConfigPage from './pages/CosmicConfigPage';
import MainSystemConfigPage from './pages/MainSystemConfigPage';
import './App.css';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <Router>
        <div className="App">
          <header className="app-header">
            <h1>业务需求工作量评估系统</h1>
          </header>
          <main className="app-main">
            <Routes>
              <Route path="/" element={<UploadPage />} />
              <Route path="/tasks" element={<TaskListPage />} />
              <Route path="/report/:taskId" element={<ReportPage />} />
              <Route path="/edit/:taskId" element={<EditPage />} />
              <Route path="/config/subsystem" element={<SubsystemConfigPage />} />
              <Route path="/config/cosmic" element={<CosmicConfigPage />} />
              <Route path="/config/mainsystem" element={<MainSystemConfigPage />} />
            </Routes>
          </main>
        </div>
      </Router>
    </ConfigProvider>
  );
}

export default App;
