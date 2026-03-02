# T009 BoardPage V2.4 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完成 `SystemProfileBoardPage` 的 v2.4 里程碑能力（三区布局、子字段级 diff 操作、时间线分页与空态、只读模式提示）。

**Architecture:** 以前端页面内状态机为中心，读取 `profile_data / ai_suggestions / ai_suggestions_previous / profile_events`，按域驱动渲染；所有写操作走既有 API（accept/rollback/put/publish）；时间线使用 `limit/offset` 分页增量加载。

**Tech Stack:** React 18, Ant Design, axios, React Testing Library, Jest

---

### Task 1: 写失败测试（TDD Red）

**Files:**
- Create: `frontend/src/__tests__/systemProfileBoardPage.v24.test.js`
- Modify: `frontend/src/pages/SystemProfileBoardPage.js`

1. 写测试：页面渲染后展示 5 域导航 + 时间线容器。
2. 写测试：事件为空时显示“暂无变更记录”。
3. 写测试：事件超 20 条时显示“加载更多”并发起第二页请求。
4. 写测试：`ai_suggestions_previous` 缺失时“恢复上一版建议”按钮禁用。
5. 运行：`cd frontend && npm test -- --watch=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js`，确认失败。

### Task 2: 最小实现（TDD Green）

**Files:**
- Modify: `frontend/src/pages/SystemProfileBoardPage.js`

1. 将页面改为三区布局（域导航 / 内容区 / 时间线）。
2. 基于 `profile_data` 渲染 5 域 12 子字段；展示 inline diff 区块和三按钮（采纳/忽略/恢复）。
3. 对接时间线接口 `GET /api/v1/system-profiles/{system_id}/profile/events?limit=20&offset=...`，支持空态与分页。
4. 回滚按钮根据 `ai_suggestions_previous` 是否存在进行禁用控制。
5. 保持既有只读权限提示与保存/发布能力。

### Task 3: 复测与收口（Refactor + Verify）

**Files:**
- Modify: `docs/v2.4/plan.md`

1. 复跑测试：`cd frontend && npm test -- --watch=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js src/__tests__/navigationAndPageTitleRegression.test.js`
2. 若通过，更新 `docs/v2.4/plan.md`：`T009` 状态与验收勾选。
3. 准备里程碑展示材料（命中 REQ-002/003/011/012/102/103）。
