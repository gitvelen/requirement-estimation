# 需求评估系统 - 设计文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档版本 | v2.1 |
| 编写日期 | 2026-01-30 |
| 基于需求 | requirements.md v2.1 |

---

## 零、实现分期说明（v2.1）

本期（2026-01-30）按“先让知识库可用、其余能力分期交付”的原则裁剪范围：

- **本期重点**：知识库可用（导入、检索、统计/指标），用于增强系统识别/功能拆分等Agent能力。
- **本期不做（延期到下一期）**：K8s + CI/CD、数据库持久化、Redis 缓存、MinIO/Milvus（服务化向量库）、生产化中间件（统一异常/请求日志/限流/Tracing等）。

本期落地架构（简化）：

```
Frontend(React) → Backend(FastAPI) → data/*.json（业务数据） + uploads/（业务文件）
                              ├→ 本地向量库（data/knowledge_store.json）
                              └→ DashScope LLM（外部服务）
```

## 一、系统架构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                         前端 (React)                        │
├─────────────────────────────────────────────────────────────┤
│  登录页  │  任务管理  │  评估页  │  配置页  │  个人中心     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                             │
├─────────────────────────────────────────────────────────────┤
│  认证中间件  │  权限中间件  │  日志中间件  │  限流中间件    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       后端服务 (Python)                      │
├─────────────────────────────────────────────────────────────┤
│  用户服务  │  任务服务  │  评估服务  │  配置服务  │  通知服务 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         数据层                               │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL  │  Milvus(向量库)  │  MinIO(文件存储)          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       外部服务                               │
├─────────────────────────────────────────────────────────────┤
│  AI评估服务  │  邮件服务  │  短信服务（预留）              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18, Ant Design 5, Axios, React Router |
| 后端 | Python 3.10+, FastAPI |
| 数据存储 | 本地文件（本期）；PostgreSQL（下一期） |
| 缓存 | 无（本期）；Redis（下一期） |
| 向量库 | 本地文件向量库（本期）；Milvus 2.3+（下一期） |
| 文件存储 | uploads/ 本地挂载（本期）；MinIO（下一期业务文件） |
| 认证 | JWT |

---

## 二、数据库设计

> 说明：本章为目标态设计。本期（v2.1）暂不落地数据库持久化，业务数据使用文件存储替代；下一期再完成落库与迁移。

### 2.1 ER图概览

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    users     │────<│expert_assignments│>────│   tasks      │
└──────────────┘     └──────────────┘     └──────────────┘
       │                                            │
       │                                            │
       v                                            v
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ user_roles   │     │  features    │     │  systems     │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            │
                            v
                     ┌──────────────┐
                     │evaluations   │
                     └──────────────┘
```

### 2.2 表结构设计

#### users（用户表）

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(50) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    display_name    VARCHAR(100) NOT NULL,
    email           VARCHAR(100),
    phone           VARCHAR(20),
    department      VARCHAR(100),
    avatar_url      VARCHAR(255),
    is_active       BOOLEAN DEFAULT true,
    last_login_at   TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
```

#### user_roles（用户角色关联表）

```sql
CREATE TABLE user_roles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL, -- 'admin', 'manager', 'expert'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, role)
);

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
```

#### user_expertise（用户专长领域表）

```sql
CREATE TABLE user_expertise (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module          VARCHAR(100) NOT NULL, -- 功能模块
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, module)
);

CREATE INDEX idx_user_expertise_user_id ON user_expertise(user_id);
```

#### tasks（任务表）

```sql
CREATE TABLE tasks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    status              VARCHAR(30) NOT NULL DEFAULT 'draft',
                       -- 'draft', 'awaiting_assignment', 'evaluating', 'completed', 'archived'
    current_round       INT DEFAULT 1,
    max_rounds          INT DEFAULT 3,
    creator_id          UUID NOT NULL REFERENCES users(id),
    ai_status           VARCHAR(20) DEFAULT 'pending',
                       -- 'pending', 'processing', 'success', 'failed'
    ai_error_message    TEXT,
    document_name       VARCHAR(255),
    document_url        VARCHAR(255),
    document_parsed_data JSONB, -- 解析后的功能点数据
    submitted_to_admin_at TIMESTAMP,
    completed_at        TIMESTAMP,
    archived_at         TIMESTAMP,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_creator_id ON tasks(creator_id);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
```

#### task_systems（任务涉及系统表）

```sql
CREATE TABLE task_systems (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    system_name     VARCHAR(100) NOT NULL,
    original_name   VARCHAR(100), -- AI识别的原始名称
    is_renamed      BOOLEAN DEFAULT false,
    is_deleted      BOOLEAN DEFAULT false,
    deleted_at      TIMESTAMP,
    deleted_by      UUID REFERENCES users(id),
    sort_order      INT DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_id, system_name)
);

CREATE INDEX idx_task_systems_task_id ON task_systems(task_id);
```

#### features（功能点表）

```sql
CREATE TABLE features (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id             UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    system_name         VARCHAR(100) NOT NULL,
    sequence            VARCHAR(20), -- 序号，如 "1.1"
    module              VARCHAR(100), -- 功能模块
    name                VARCHAR(255) NOT NULL, -- 功能点名称
    description         TEXT, -- 业务描述
    inputs              JSONB DEFAULT '[]'::jsonb, -- 输入数组
    outputs             JSONB DEFAULT '[]'::jsonb, -- 输出数组
    dependencies        JSONB DEFAULT '[]'::jsonb, -- 依赖项数组
    ai_estimated_days   DECIMAL(5,2) NOT NULL, -- AI预估人天
    source              VARCHAR(20) DEFAULT 'ai', -- 'ai' or 'manual'
    remark              TEXT, -- 备注
    is_modified         BOOLEAN DEFAULT false, -- 项目经理是否修改过
    modified_fields     JSONB DEFAULT '[]'::jsonb, -- 被修改的字段列表
    added_by_manager    BOOLEAN DEFAULT false, -- 是否为项目经理新增
    deleted             BOOLEAN DEFAULT false,
    sort_order          INT DEFAULT 0,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_features_task_id ON features(task_id);
CREATE INDEX idx_features_system_name ON features(system_name);
```

#### expert_assignments（专家分配表）

```sql
CREATE TABLE expert_assignments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id),
    invite_token    VARCHAR(100) UNIQUE NOT NULL, -- 当前有效Token
    invite_link     VARCHAR(255),
    invite_status   VARCHAR(20) DEFAULT 'active', -- active/revoked
    invite_revoked_at TIMESTAMP,
    has_submitted   BOOLEAN DEFAULT false,
    submitted_round INT DEFAULT 0, -- 已提交到第几轮
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_id, user_id)
);

CREATE INDEX idx_expert_assignments_task_id ON expert_assignments(task_id);
CREATE INDEX idx_expert_assignments_user_id ON expert_assignments(user_id);
CREATE INDEX idx_expert_assignments_token ON expert_assignments(invite_token);
```

#### expert_invite_tokens（专家邀请Token历史表）

```sql
CREATE TABLE expert_invite_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id   UUID NOT NULL REFERENCES expert_assignments(id) ON DELETE CASCADE,
    invite_token    VARCHAR(100) UNIQUE NOT NULL,
    invite_link     VARCHAR(255),
    status          VARCHAR(20) DEFAULT 'active', -- active/revoked/expired
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at      TIMESTAMP,
    revoked_reason  TEXT
);

CREATE INDEX idx_invite_tokens_assignment_id ON expert_invite_tokens(assignment_id);
CREATE INDEX idx_invite_tokens_token ON expert_invite_tokens(invite_token);
```

#### evaluations（专家评估表）

```sql
CREATE TABLE evaluations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    feature_id      UUID NOT NULL REFERENCES features(id) ON DELETE CASCADE,
    expert_id       UUID NOT NULL REFERENCES users(id),
    round           INT NOT NULL, -- 第几轮评估
    estimated_days  DECIMAL(5,2) NOT NULL, -- 专家估算人天
    submitted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_id, feature_id, expert_id, round)
);

CREATE INDEX idx_evaluations_task_id ON evaluations(task_id);
CREATE INDEX idx_evaluations_feature_id ON evaluations(feature_id);
CREATE INDEX idx_evaluations_expert_id ON evaluations(expert_id);
```

#### evaluation_submissions（评估提交记录表）

```sql
CREATE TABLE evaluation_submissions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    expert_id       UUID NOT NULL REFERENCES users(id),
    round           INT NOT NULL,
    submitted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    withdrawn_at    TIMESTAMP,
    UNIQUE(task_id, expert_id, round)
);

CREATE INDEX idx_evaluation_submissions_task_id ON evaluation_submissions(task_id);
```

#### systems（系统配置表）

```sql
CREATE TABLE systems (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) UNIQUE NOT NULL,
    type            VARCHAR(20) NOT NULL, -- 'main' or 'sub'
    parent_id       UUID REFERENCES systems(id),
    description     TEXT,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_systems_type ON systems(type);
CREATE INDEX idx_systems_parent_id ON systems(parent_id);
```

#### estimation_rules（估算规则表）

```sql
CREATE TABLE estimation_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    system_id       UUID REFERENCES systems(id),
    system_name     VARCHAR(100) NOT NULL,
    module          VARCHAR(100) NOT NULL,
    complexity      VARCHAR(20) NOT NULL, -- '低', '中', '高'
    base_days       DECIMAL(5,2) NOT NULL,
    description     TEXT,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_estimation_rules_system_id ON estimation_rules(system_id);
```

#### knowledge_documents（知识库文档表）

```sql
CREATE TABLE knowledge_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    system_id       UUID REFERENCES systems(id),
    system_name     VARCHAR(100) NOT NULL,
    category        VARCHAR(30) NOT NULL,
                    -- 'requirement', 'technical', 'test', 'history'
    file_name       VARCHAR(255) NOT NULL,
    file_url        VARCHAR(255) NOT NULL,
    file_size       BIGINT,
    uploaded_by     UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_knowledge_docs_system_id ON knowledge_documents(system_id);
CREATE INDEX idx_knowledge_docs_category ON knowledge_documents(category);
```

#### knowledge_retrieval_logs（知识库检索命中记录表）

```sql
CREATE TABLE knowledge_retrieval_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    feature_id      UUID REFERENCES features(id),
    knowledge_type  VARCHAR(30) NOT NULL, -- 'requirement' | 'technical' | 'test' | 'history'
    hit_count       INT NOT NULL DEFAULT 0,
    avg_similarity  DECIMAL(5,2),
    max_similarity  DECIMAL(5,2),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_knowledge_logs_task_id ON knowledge_retrieval_logs(task_id);
CREATE INDEX idx_knowledge_logs_type ON knowledge_retrieval_logs(knowledge_type);
CREATE INDEX idx_knowledge_logs_created_at ON knowledge_retrieval_logs(created_at DESC);
```

#### notifications（通知表）

```sql
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type            VARCHAR(50) NOT NULL,
    title           VARCHAR(255) NOT NULL,
    content         TEXT,
    task_id         UUID REFERENCES tasks(id),
    is_read         BOOLEAN DEFAULT false,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
```

#### activity_logs（操作日志表）

```sql
CREATE TABLE activity_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    type            VARCHAR(50) NOT NULL,
    description     TEXT NOT NULL,
    ip_address      VARCHAR(45),
    task_id         UUID REFERENCES tasks(id),
    metadata        JSONB,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_created_at ON activity_logs(created_at DESC);
```

#### deviation_records（偏离度记录表）

```sql
CREATE TABLE deviation_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    feature_id      UUID NOT NULL REFERENCES features(id),
    round           INT NOT NULL,
    ai_days         DECIMAL(5,2) NOT NULL,
    expert_avg_days DECIMAL(5,2) NOT NULL,
    deviation_rate  DECIMAL(5,2) NOT NULL, -- 百分比
    is_high_deviation BOOLEAN DEFAULT false,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_id, feature_id, round)
);

CREATE INDEX idx_deviation_records_task_id ON deviation_records(task_id);
```

#### report_versions（报告版本表）

```sql
CREATE TABLE report_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    round           INT NOT NULL,
    version         INT NOT NULL,
    file_name       VARCHAR(255) NOT NULL,
    file_url        VARCHAR(255) NOT NULL,
    generated_by    UUID REFERENCES users(id),
    status          VARCHAR(20) DEFAULT 'generated', -- generated/failed
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_id, round, version)
);

CREATE INDEX idx_report_versions_task_id ON report_versions(task_id);
CREATE INDEX idx_report_versions_round ON report_versions(task_id, round);
CREATE INDEX idx_report_versions_created_at ON report_versions(created_at DESC);
```

#### ai_effect_snapshots（AI效果指标快照表）

```sql
CREATE TABLE ai_effect_snapshots (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id                 UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    round                   INT NOT NULL,
    manager_id              UUID NOT NULL REFERENCES users(id),
    system_name             VARCHAR(100),
    module                  VARCHAR(100), -- 功能模块
    human_day_accuracy      DECIMAL(5,2),
    feature_retention_rate  DECIMAL(5,2),
    field_modification_rate DECIMAL(5,2),
    knowledge_hit_rate      DECIMAL(5,2),
    system_recognition_rate DECIMAL(5,2),
    new_feature_rate        DECIMAL(5,2),
    manager_trust_score     DECIMAL(5,2),
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_effect_task_id ON ai_effect_snapshots(task_id);
CREATE INDEX idx_ai_effect_manager_id ON ai_effect_snapshots(manager_id);
CREATE INDEX idx_ai_effect_system_module ON ai_effect_snapshots(system_name, module);
CREATE INDEX idx_ai_effect_created_at ON ai_effect_snapshots(created_at DESC);
```

---

## 三、API接口设计

### 3.1 接口规范

#### 请求规范

- **Content-Type**: `application/json`（除文件上传外）
- **认证**: `Authorization: Bearer {token}`
- **分页**: `?page=1&size=20`
- **排序**: `?sort=created_at&order=desc`

#### 响应规范

**成功响应**
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

**错误响应**
```json
{
  "code": 400,
  "message": "error message",
  "detail": "error detail"
}
```

### 3.2 接口清单

#### 认证模块 (Auth)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | /api/v1/auth/login | 用户登录 | 公开 |
| GET | /api/v1/auth/me | 获取当前用户 | 登录 |
| POST | /api/v1/auth/change-password | 修改密码 | 登录 |

#### 任务模块 (Tasks)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | /api/v1/tasks | 创建任务 | 经理 |
| GET | /api/v1/tasks | 获取任务列表 | 登录 |
| GET | /api/v1/tasks/{id} | 获取任务详情 | 登录 |
| GET | /api/v1/tasks/{id}/ai-progress | AI评估进度 | 登录 |
| DELETE | /api/v1/tasks/{id} | 删除任务 | 创建者/管理员 |
| POST | /api/v1/tasks/{id}/submit-to-admin | 提交给管理员 | 创建者 |
| POST | /api/v1/tasks/{id}/assign-experts | 分配专家 | 管理员 |
| POST | /api/v1/tasks/{id}/invites/{assignmentId}/resend | 重发邀请 | 管理员 |
| POST | /api/v1/tasks/{id}/invites/{assignmentId}/revoke | 撤销邀请 | 管理员 |
| GET | /api/v1/tasks/{id}/report | 下载最新报告 | 管理员/创建者 |
| GET | /api/v1/tasks/{id}/reports | 报告版本列表 | 管理员/创建者 |
| GET | /api/v1/tasks/{id}/reports/{rid} | 下载指定报告版本 | 管理员/创建者 |
| PUT | /api/v1/tasks/{id}/archive | 归档任务 | 管理员/创建者 |

#### 评估模块 (Evaluation)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/evaluation/{id} | 获取评估数据（第二/三轮仅高偏离） | 被邀请专家 |
| POST | /api/v1/evaluation/{id}/submit | 提交评估 | 被邀请专家 |
| POST | /api/v1/evaluation/{id}/withdraw | 撤回评估（报告未生成前） | 被邀请专家 |
| POST | /api/v1/evaluation/{id}/draft | 保存草稿 | 被邀请专家 |
| GET | /api/v1/evaluation/{id}/high-deviation | 高偏离功能点 | 被邀请专家 |
| GET | /api/v1/evaluation/{id}/progress | 评估进度 | 管理员/创建者 |

#### 功能点模块 (Features)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | /api/v1/tasks/{id}/features | 添加功能点 | 创建者 |
| PUT | /api/v1/tasks/{id}/features/{fid} | 更新功能点 | 创建者 |
| DELETE | /api/v1/tasks/{id}/features/{fid} | 删除功能点 | 创建者 |
| PUT | /api/v1/tasks/{id}/features/batch | 批量更新 | 创建者 |
| POST | /api/v1/requirement/systems/{task_id} | 新增系统Tab（默认自动拆分） | 创建者 |
| POST | /api/v1/requirement/systems/{task_id}/{system}/rebreakdown | 重新拆分系统（覆盖该系统功能点） | 创建者 |
| DELETE | /api/v1/requirement/systems/{task_id}/{system_name} | 删除系统Tab | 创建者 |
| PUT | /api/v1/requirement/systems/{task_id}/{system_name}/rename | 重命名系统 | 创建者 |

#### 用户模块 (Users)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/users | 获取用户列表 | 管理员 |
| POST | /api/v1/users | 创建用户 | 管理员 |
| POST | /api/v1/users/batch-import | 批量导入 | 管理员 |
| PUT | /api/v1/users/{id} | 更新用户 | 管理员 |
| PUT | /api/v1/users/{id}/status | 启用/禁用 | 管理员 |
| DELETE | /api/v1/users/{id} | 删除用户 | 管理员 |

#### 配置模块 (Config)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/config/systems | 获取系统列表 | 登录 |
| POST | /api/v1/config/systems | 创建系统 | 管理员 |
| PUT | /api/v1/config/systems/{id} | 更新系统 | 管理员 |
| DELETE | /api/v1/config/systems/{id} | 删除系统 | 管理员 |
| GET | /api/v1/config/estimation-rules | 获取估算规则 | 登录 |
| POST | /api/v1/config/estimation-rules | 创建规则 | 管理员 |
| PUT | /api/v1/config/estimation-rules/{id} | 更新规则 | 管理员 |

#### 知识库模块 (Knowledge)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | /api/v1/knowledge/import | 导入系统知识（DOCX/PPTX，按主系统维度） | 经理 |
| POST | /api/v1/knowledge/search | 检索相似系统知识（需 system_name） | 管理员/经理 |
| GET | /api/v1/knowledge/stats | 统计信息（支持按 system_name 过滤） | 管理员/经理 |
| GET | /api/v1/knowledge/evaluation-metrics | 效果评估指标 | 管理员/经理 |
| POST | /api/v1/knowledge/rebuild-index | 重建索引（本地向量库） | 管理员 |
| GET | /api/v1/knowledge/health | 健康检查 | 管理员/经理 |

#### 通知模块 (Notifications)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/notifications | 通知列表 | 登录 |
| PUT | /api/v1/notifications/{id}/read | 标记已读 | 所有者 |
| PUT | /api/v1/notifications/read-all | 全部已读 | 登录 |
| DELETE | /api/v1/notifications/{id} | 删除通知 | 所有者 |
| DELETE | /api/v1/notifications/clear-read | 清空已读 | 登录 |
| GET | /api/v1/notifications/unread-count | 未读数量 | 登录 |

#### 个人中心模块 (Profile)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/profile | 个人资料 | 登录 |
| PUT | /api/v1/profile | 更新资料 | 登录 |
| POST | /api/v1/profile/avatar | 上传头像 | 登录 |
| GET | /api/v1/profile/activity-logs | 操作记录 | 登录 |
| GET | /api/v1/profile/my-evaluations | 我的评估 | 专家 |
| GET | /api/v1/profile/my-tasks | 我的任务 | 经理 |

#### 报告模块 (Reports)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/reports/ai-effect | AI效果报告 | 管理员/经理/专家 |

说明：支持筛选参数 `system_name`、`module`、`manager_id`、`date_from`、`date_to`、`round`，时间维度默认按“报告版本生成时间”统计；**专家仅返回本人参与任务的汇总匿名指标**，不展示项目经理维度（且忽略 `manager_id` 过滤）。

### 3.3 核心接口详解

#### 3.3.1 用户登录

```
POST /api/v1/auth/login

Request:
{
  "username": "zhangsan",
  "password": "password123"
}

Response 200:
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "uuid",
      "username": "zhangsan",
      "displayName": "张三",
      "roles": ["manager", "expert"],
      "avatar": "url"
    }
  }
}

Response 401:
{
  "code": 401,
  "message": "用户名或密码错误"
}
```

#### 3.3.2 创建任务

```
POST /api/v1/tasks
Content-Type: multipart/form-data

Request:
{
  "file": <document>,
  "name": "XXX项目评估",
  "description": "项目描述"
}

Response 200:
{
  "code": 200,
  "message": "success",
  "data": {
    "taskId": "uuid",
    "status": "processing",
    "message": "AI正在分析文档，请稍候..."
  }
}
```

#### 3.3.3 获取评估数据

```
GET /api/v1/evaluation/{taskId}
Authorization: Bearer {token}

Response 200:
{
  "code": 200,
  "message": "success",
  "data": {
    "task": {
      "id": "uuid",
      "name": "XXX项目评估",
      "status": "evaluating",
      "currentRound": 1,
      "systems": ["核心系统", "渠道系统"]
    },
    "features": {
      "核心系统": [
        {
          "id": "uuid",
          "sequence": "1.1",
          "module": "账户管理",
          "name": "开立个人账户",
          "description": "...",
          "inputs": ["身份证信息"],
          "outputs": ["账户号"],
          "dependencies": ["客户信息系统"],
          "aiEstimatedDays": 5.0,
          "source": "ai",
          "remark": null,
          "myEvaluation": null
        }
      ],
      "渠道系统": [...]
    },
    "myEvaluation": {
      "hasSubmitted": false,
      "submittedRound": 0,
      "draftData": {}
    },
    "highDeviationFeatures": [] // 第二轮时返回
  }
}
```

#### 3.3.4 提交评估

```
POST /api/v1/evaluation/{taskId}/submit
Authorization: Bearer {token}

Request:
{
  "round": 1,
  "evaluations": {
    "featureId1": 5.5,
    "featureId2": 3.0
  }
}

Response 200:
{
  "code": 200,
  "message": "评估已提交",
  "data": {
    "round": 1,
    "submittedAt": "2025-01-28T10:00:00Z"
  }
}
```

#### 3.3.5 分配专家

```
POST /api/v1/tasks/{taskId}/assign-experts
Authorization: Bearer {admin_token}

Request:
{
  "expertIds": ["expert1_uuid", "expert2_uuid", "expert3_uuid"]
}

Response 200:
{
  "code": 200,
  "message": "success",
  "data": {
    "inviteLinks": [
      {
        "expertId": "expert1_uuid",
        "expertName": "专家A",
        "link": "https://domain.com/evaluate/taskId/token1"
      },
      {
        "expertId": "expert2_uuid",
        "expertName": "专家B",
        "link": "https://domain.com/evaluate/taskId/token2"
      },
      {
        "expertId": "expert3_uuid",
        "expertName": "专家C",
        "link": "https://domain.com/evaluate/taskId/token3"
      }
    ]
  }
}
```

---

## 四、前端设计

### 4.1 目录结构

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── api/              # API接口
│   │   ├── auth.js
│   │   ├── tasks.js
│   │   ├── evaluation.js
│   │   ├── users.js
│   │   ├── config.js
│   │   └── knowledge.js
│   ├── assets/           # 静态资源
│   │   ├── styles/
│   │   │   ├── global.css
│   │   │   └── variables.css
│   │   └── images/
│   ├── components/       # 公共组件
│   │   ├── Layout/
│   │   │   ├── MainLayout.js
│   │   │   └── Sidebar.js
│   │   ├── Common/
│   │   │   ├── PageHeader.js
│   │   │   ├── DataTable.js
│   │   │   └── StatusTag.js
│   │   └── Evaluation/
│   │       ├── FeatureTable.js
│   │       ├── SystemTabs.js
│   │       └── EditableCell.js
│   ├── contexts/         # Context
│   │   ├── AuthContext.js
│   │   └── NotificationContext.js
│   ├── hooks/            # 自定义Hooks
│   │   ├── useAuth.js
│   │   ├── usePermission.js
│   │   └── useWebSocket.js
│   ├── pages/            # 页面组件
│   │   ├── Auth/
│   │   │   └── LoginPage.js
│   │   ├── Tasks/
│   │   │   ├── TaskListPage.js
│   │   │   ├── TaskDetailPage.js
│   │   │   └── CreateTaskPage.js
│   │   ├── Evaluation/
│   │   │   └── EvaluationPage.js
│   │   ├── Config/
│   │   │   ├── SystemConfigPage.js
│   │   │   ├── SubsystemConfigPage.js
│   │   │   └── RuleConfigPage.js
│   │   ├── Users/
│   │   │   └── UserManagePage.js
│   │   ├── KnowledgePage.js
│   │   ├── AIEffectReportPage.js
│   │   ├── Profile/
│   │   │   └── ProfilePage.js
│   │   └── Notifications/
│   │       └── NotificationPage.js
│   ├── router/          # 路由配置
│   │   └── index.js
│   ├── store/           # 状态管理
│   │   └── index.js
│   ├── utils/           # 工具函数
│   │   ├── request.js
│   │   ├── format.js
│   │   └── constants.js
│   ├── App.js
│   └── index.js
├── package.json
└── vite.config.js
```

### 4.2 路由配置

```javascript
// router/index.js
const routes = [
  {
    path: '/login',
    component: lazy(() => import('../pages/Auth/LoginPage')),
    public: true
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      // 任务相关
      { path: '', component: lazy(() => import('../pages/Tasks/TaskListPage')) },
      { path: 'tasks/create', component: lazy(() => import('../pages/Tasks/CreateTaskPage')), permission: 'manager' },
      { path: 'tasks/:id', component: lazy(() => import('../pages/Tasks/TaskDetailPage')) },

      // 评估相关
      { path: 'evaluate/:taskId/:token', component: lazy(() => import('../pages/Evaluation/EvaluationPage')), permission: 'expert' },

      // 配置相关
      { path: 'config/systems', component: lazy(() => import('../pages/Config/SystemConfigPage')), permission: 'admin' },
      { path: 'config/rules', component: lazy(() => import('../pages/Config/RuleConfigPage')), permission: 'admin' },
      { path: 'config/users', component: lazy(() => import('../pages/Users/UserManagePage')), permission: 'admin' },

      // 知识库相关
      { path: 'knowledge', component: lazy(() => import('../pages/KnowledgePage')) },
      { path: 'reports/ai-effect', component: lazy(() => import('../pages/AIEffectReportPage')) },

      // 个人中心
      { path: 'profile', component: lazy(() => import('../pages/Profile/ProfilePage')) },

      // 通知
      { path: 'notifications', component: lazy(() => import('../pages/Notifications/NotificationPage')) }
    ]
  }
];
```

### 4.3 核心组件设计

#### 4.3.1 MainLayout（主布局）

```jsx
<Layout style={{ minHeight: '100vh' }}>
  <Sidebar />
  <Layout>
    <Header />
    <Content className="main-content">
      <Outlet />
    </Content>
  </Layout>
</Layout>
```

#### 4.3.2 Sidebar（侧边栏）

根据用户角色动态渲染菜单：

```javascript
const menusByRole = {
  admin: [
    { group: '任务管理', items: [
      { key: 'all-tasks', label: '任务管理', path: '/tasks' }
    ]},
    { group: '配置管理', items: [
      { key: 'system-list', label: '系统清单', path: '/config/system-list' },
      { key: 'rules', label: '规则管理', path: '/config/cosmic' },
      { key: 'users', label: '用户管理', path: '/users' }
    ]},
    { group: '效果统计', items: [
      { key: 'ai-report', label: 'AI效果报告', path: '/reports/ai-effect' }
    ]},
    { group: '个人', items: [
      { key: 'notifications', label: '消息通知', path: '/notifications', badge: unreadCount },
      { key: 'profile', label: '个人中心', path: '/profile' }
    ]}
  ],
  manager: [
    { group: '任务管理', items: [
      { key: 'my-tasks', label: '任务管理', path: '/tasks/my-tasks' }
    ]},
    { group: '配置管理', items: [
      { key: 'knowledge', label: '知识库管理', path: '/knowledge' }
    ]},
    { group: '效果统计', items: [
      { key: 'ai-report', label: 'AI效果报告', path: '/reports/ai-effect' }
    ]},
    { group: '个人', items: [
      { key: 'notifications', label: '消息通知', path: '/notifications', badge: unreadCount },
      { key: 'profile', label: '个人中心', path: '/profile' }
    ]}
  ],
  expert: [
    { group: '任务管理', items: [
      { key: 'my-evaluations', label: '任务管理', path: '/tasks/my-evaluations' }
    ]},
    { group: '效果统计', items: [
      { key: 'ai-report', label: 'AI效果报告', path: '/reports/ai-effect' }
    ]},
    { group: '个人', items: [
      { key: 'notifications', label: '消息通知', path: '/notifications', badge: unreadCount },
      { key: 'profile', label: '个人中心', path: '/profile' }
    ]}
  ]
};
```

#### 4.3.3 FeatureTable（功能点表格）

核心交互组件：

```jsx
<Table
  columns={columns}
  dataSource={features}
  rowKey="id"
  pagination={false}
  scroll={{ x: 1400 }}
  rowClassName={(record) => {
    if (highDeviationIds.includes(record.id)) return 'high-deviation-row';
    if (record.addedByManager) return 'manual-added-row';
    return '';
  }}
  onRow={(record) => ({
    onClick: () => handleRowClick(record)
  })}
/>

// 可编辑单元格
const EditableCell = ({ value, onChange, isAIValue }) => {
  const [editing, setEditing] = useState(false);

  return (
    <div
      className={cn('editable-cell', {
        'ai-value': isAIValue && !editing,
        'expert-value': !isAIValue || editing
      })}
      onClick={() => setEditing(true)}
    >
      {editing ? (
        <InputNumber
          defaultValue={value}
          autoFocus
          min={0.5}
          max={50}
          step={0.5}
          onBlur={(e) => {
            onChange(e.target.value);
            setEditing(false);
          }}
          onPressEnter={() => setEditing(false)}
        />
      ) : (
        <span>{value}</span>
      )}
    </div>
  );
};
```

### 4.4 样式规范

#### 4.4.1 CSS变量

```css
:root {
  /* 主色调 */
  --color-primary: #1890ff;
  --color-primary-hover: #40a9ff;
  --color-primary-active: #096dd9;

  /* 中性色 */
  --color-text-primary: #262626;
  --color-text-secondary: #595959;
  --color-text-tertiary: #8c8c8c;
  --color-text-disabled: #bfbfbf;

  /* 背景色 */
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #f5f5f5;
  --color-bg-tertiary: #fafafa;

  /* 边框色 */
  --color-border: #d9d9d9;
  --color-border-light: #f0f0f0;

  /* 功能色 */
  --color-success: #52c41a;
  --color-warning: #faad14;
  --color-error: #ff4d4f;
  --color-info: #1890ff;

  /* AI值样式 */
  --color-ai-value: #8c8c8c;
  --color-expert-bg: #e6f7ff;
  --color-expert-value: #262626;

  /* 高偏离样式 */
  --color-high-deviation-bg: #fff1f0;
  --color-high-deviation-border: #ffccc7;

  /* 间距 */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;

  /* 圆角 */
  --border-radius-sm: 4px;
  --border-radius-md: 8px;

  /* 阴影 */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.03);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
}
```

#### 4.4.2 评估表格样式

```css
.feature-table .ai-value {
  color: var(--color-ai-value);
}

.feature-table .expert-value {
  color: var(--color-expert-value);
  background-color: var(--color-expert-bg);
  padding: 2px 8px;
  border-radius: var(--border-radius-sm);
}

.feature-table .high-deviation-row {
  background-color: var(--color-high-deviation-bg);
}

.feature-table .high-deviation-row:hover {
  background-color: #ffccc7;
}

.editable-cell {
  cursor: pointer;
  transition: all 0.2s;
}

.editable-cell:hover {
  background-color: #f5f5f5;
}
```

---

## 五、后端设计

### 5.1 目录结构

```
backend/
├── api/
│   ├── __init__.py
│   ├── auth.py              # 认证相关
│   ├── tasks.py             # 任务相关
│   ├── evaluation.py        # 评估相关
│   ├── users.py             # 用户相关
│   ├── config.py            # 配置相关
│   ├── knowledge.py         # 知识库相关
│   └── notifications.py     # 通知相关
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── task.py
│   ├── feature.py
│   ├── evaluation.py
│   ├── system.py
│   └── notification.py
├── schemas/
│   ├── __init__.py
│   ├── user.py
│   ├── task.py
│   ├── evaluation.py
│   └── common.py
├── services/
│   ├── __init__.py
│   ├── auth_service.py
│   ├── task_service.py
│   ├── evaluation_service.py
│   ├── ai_service.py        # AI评估服务
│   ├── notification_service.py
│   └── deviation_service.py # 偏离度计算
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── security.py
│   ├── deps.py             # 依赖注入
│   └── middleware.py
├── db/
│   ├── __init__.py
│   ├── session.py
│   └── base.py
├── utils/
│   ├── __init__.py
│   ├── jwt.py
│   ├── password.py
│   └── excel.py            # Excel导入导出
├── app.py                   # FastAPI应用
└── main.py                  # 启动入口
```

### 5.2 核心服务设计

#### 5.2.1 AuthService（认证服务）

```python
class AuthService:
    async def login(self, username: str, password: str) -> TokenResponse:
        # 1. 验证用户名密码
        # 2. 检查用户状态
        # 3. 生成JWT token
        # 4. 记录登录日志
        # 5. 返回token和用户信息

    async def get_current_user(self, token: str) -> User:
        # 1. 解析JWT token
        # 2. 验证token有效性
        # 3. 返回用户信息（包含角色）

    async def change_password(self, user_id: str, old_pwd: str, new_pwd: str):
        # 1. 验证旧密码
        # 2. 更新新密码
        # 3. 记录操作日志
```

#### 5.2.2 TaskService（任务服务）

```python
class TaskService:
    async def create_task(self, file: UploadFile, creator_id: str, name: str, description: str) -> str:
        # 1. 保存文件到本地uploads（本期）；MinIO（下一期）
        # 2. 创建任务记录（status=draft, ai_status=processing）
        # 3. 异步调用AI评估服务
        # 4. 返回task_id

    async def get_ai_progress(self, task_id: str) -> AIProgress:
        # 1. 查询任务状态
        # 2. 如果AI评估中，返回进度
        # 3. 如果完成，返回解析结果

    async def submit_to_admin(self, task_id: str, user_id: str):
        # 1. 验证用户权限（创建者）
        # 2. 检查AI评估状态
        # 3. 更新任务状态为awaiting_assignment
        # 4. 发送通知给管理员

    async def assign_experts(self, task_id: str, expert_ids: List[str]) -> List[InviteLink]:
        # 1. 验证权限（管理员）
        # 2. 为每个专家生成invite_token
        # 3. 创建/更新expert_assignment记录
        # 4. 生成invite_link并记录invite_token历史
        # 5. 如为重分配/重发，撤销旧token（立即失效）
        # 6. 发送通知给专家

    async def resend_invite(self, assignment_id: str) -> InviteLink:
        # 1. 生成新invite_token
        # 2. 撤销旧token并记录历史
        # 3. 返回新邀请链接

    async def revoke_invite(self, assignment_id: str):
        # 1. 撤销当前invite_token
        # 2. 更新assignment状态为revoked

    async def get_task_detail(self, task_id: str, user: User) -> TaskDetail:
        # 1. 验证用户权限
        # 2. 查询任务基本信息
        # 3. 根据角色返回不同数据：
        #    - 管理员：全部信息
        #    - 项目经理：基本信息+进度
        #    - 专家：基本信息+我的评估状态
```

#### 5.2.3 EvaluationService（评估服务）

```python
class EvaluationService:
    async def get_evaluation_data(self, task_id: str, token: str, expert: User) -> EvaluationData:
        # 1. 验证invite_token
        # 2. 查询任务功能点（按系统分组）
        # 3. 查询专家的评估记录（本轮）
        # 4. 如果是第二/三轮，仅返回高偏离功能点
        # 5. 不返回上一轮专家的历史值（避免锚定效应）

    async def submit_evaluation(self, task_id: str, expert_id: str, round: int, evaluations: Dict):
        # 1. 验证专家权限（已被邀请）
        # 2. 保存或更新评估记录
        # 3. 创建提交记录
        # 4. 检查是否所有人都提交了
        # 5. 如果是最后一人，触发偏离度计算
        # 6. 生成本轮报告PDF版本与AI效果指标快照

    async def withdraw_evaluation(self, task_id: str, expert_id: str, round: int):
        # 1. 验证权限
        # 2. 仅允许在报告未生成前撤回
        # 3. 删除提交记录
        # 4. 回滚偏离度记录与任务状态/轮次进度
        # 5. 保留评估记录作为草稿

    async def save_draft(self, task_id: str, expert_id: str, evaluations: Dict):
        # 1. 保存草稿数据
        # 2. 返回保存时间
```

#### 5.2.4 DeviationService（偏离度服务）

```python
class DeviationService:
    async def calculate_deviation(self, task_id: str, round: int) -> DeviationResult:
        # 1. 查询所有专家的评估记录
        # 2. 对每个功能点计算：
        #    - 专家均值
        #    - 偏离度 = |均值 - AI| / AI × 100%
        # 3. 统计高偏离功能点（>20%）
        # 4. 保存偏离度记录
        # 5. 生成本轮报告PDF版本
        # 6. 生成AI效果指标快照
        # 7. 返回统计结果

    async def check_need_next_round(self, task_id: str, round: int) -> bool:
        # 1. 查询偏离度记录
        # 2. 判断是否有高偏离
        # 3. 如果有且round < max_rounds，返回true
        # 4. 否则返回false

    async def start_next_round(self, task_id: str):
        # 1. 更新任务current_round
        # 2. 下一轮仅评估高偏离功能点
        # 3. 发送通知给专家

    async def rollback_round(self, task_id: str, round: int):
        # 1. 删除/失效当前轮偏离度记录
        # 2. 回滚任务进度与提交状态
```

#### 5.2.5 ReportService（报告服务）

```python
class ReportService:
    async def generate_round_report(self, task_id: str, round: int) -> str:
        # 1. 汇总AI/专家/均值/偏离度数据
        # 2. 生成PDF报告文件
        # 3. 写入report_versions（版本号按轮次递增）
        # 4. 返回报告URL/ID

    async def list_reports(self, task_id: str) -> List[ReportVersion]:
        # 返回任务的全部报告版本
```

#### 5.2.6 AIService（AI评估服务）

```python
class AIService:
    async def process_document(self, task_id: str, file_url: str):
        # 1. 从本地uploads读取文件（本期）；MinIO（下一期）
        # 2. 调用文档解析服务
        # 3. 识别功能点
        # 4. 调用知识库检索系统画像（system_profile）用于校准（系统识别/功能拆分边界）
        # 5. 预估人天数
        # 6. 识别输入/输出/依赖项
        # 7. 识别涉及系统
        # 8. 更新任务状态
        # 9. 通知项目经理

    async def get_progress(self, task_id: str) -> AIProgress:
        # 返回AI评估进度
```

##### 5.2.6.1 知识库校准（A档）

> 说明：知识库仅维护系统画像（system_profile），不维护估算案例；主要用于提升“涉及改造的系统”识别准确率与“按系统拆分”归属合理性。人天仅作参考值。

- 系统识别：跨系统检索 system_profile → 形成候选系统榜单 → LLM 输出 systems + 置信度/理由/疑问清单（含知识引用）
- 功能点拆分：按系统检索 system_profile 作为边界卡片；在功能点“备注”写入归属依据/系统约束/集成点/知识引用/待确认
- 归属复核：对高风险功能点二次跨系统检索，仅提示“建议复核”，不自动改动归属
- 人机协作：编辑页顶部展示系统校准卡片；支持项目经理新增系统Tab（默认自动拆分）

#### 5.2.7 AIEffectService（AI效果报告服务）

```python
class AIEffectService:
    async def build_snapshot(self, task_id: str, round: int):
        # 1. 读取功能点/系统/评估数据
        # 2. 汇总AI效果指标（按系统/模块/经理）
        # 3. 写入ai_effect_snapshots

    async def query_report(self, filters: Dict) -> ReportData:
        # 根据时间/系统/模块/项目经理维度聚合展示
```

#### 5.2.8 NotificationService（通知服务）

```python
class NotificationService:
    async def create_notification(self, user_ids: List[str], type: str, title: str, content: str, task_id: str = None):
        # 批量创建通知

    async def mark_as_read(self, notification_id: str, user_id: str):
        # 标记已读

    async def mark_all_as_read(self, user_id: str):
        # 全部已读

    async def get_unread_count(self, user_id: str) -> int:
        # 未读数量

    async def notify_task_assigned(self, task_id: str):
        # 通知管理员有新任务待分配

    async def notify_expert_invited(self, task_id: str, expert_ids: List[str]):
        # 通知专家有新评估任务

    async def notify_next_round(self, task_id: str, expert_ids: List[str], round: int):
        # 通知专家进入下一轮

    async def notify_report_generated(self, task_id: str, creator_id: str):
        # 通知报告生成
```

### 5.3 中间件设计

> 说明：本章为目标态设计。本期（v2.1）不做生产化中间件建设，仅保留必要的鉴权与角色校验。

```python
# core/middleware.py

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # 认证中间件
    if request.url.path.startswith("/api/v1/auth/login"):
        return await call_next(request)

    token = request.headers.get("Authorization")
    if not token:
        return JSONResponse(status_code=401, content={"detail": "未授权"})

    user = await verify_token(token)
    if not user:
        return JSONResponse(status_code=401, content={"detail": "token无效"})

    request.state.user = user
    response = await call_next(request)
    return response

@app.middleware("http")
async def permission_middleware(request: Request, call_next):
    # 权限中间件
    user = request.state.user
    required_role = get_required_role(request.url.path, request.method)

    if required_role and required_role not in user.roles:
        return JSONResponse(status_code=403, content={"detail": "权限不足"})

    return await call_next(request)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # 日志中间件
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.2f}s")
    return response
```

---

## 六、安全设计

### 6.1 认证与授权

- **认证方式**: JWT Token
- **Token有效期**: 24小时
- **刷新机制**: 支持refresh_token
- **密码加密**: bcrypt

### 6.2 权限控制

- **RBAC模型**: 基于角色的访问控制
- **接口级权限**: 每个接口定义所需角色
- **数据级权限**: 用户只能访问自己创建的任务

### 6.3 数据安全

- **敏感数据加密**: 密码、手机号加密存储
- **SQL注入防护**: 使用ORM参数化查询
- **XSS防护**: 前端输入过滤
- **CSRF防护**: Token验证

### 6.4 文件安全

- **文件类型限制**: 只允许.docx/.xlsx/.pdf
- **文件大小限制**: 单文件最大10MB
- **病毒扫描**: 集成ClamAV

---

## 七、部署架构

> 说明：本期（v2.1）仅交付 Docker Compose 单机部署（无K8s/CI/CD）。知识库采用本地文件向量库，不需要额外依赖服务；K8s、多副本、Redis/PostgreSQL、MinIO/Milvus 等为目标态设计，延期到下一期。

### 7.1 开发环境（本期）

```
┌─────────────────────────────────────────────────────────────┐
│                       Docker Compose                        │
├─────────────────────────────────────────────────────────────┤
│  frontend │  backend                                            │
│     :80  │    :443                                             │
└─────────────────────────────────────────────────────────────┘
（下一期可选：milvus/minio/etcd，用于服务化向量库）
```

### 7.2 生产环境（目标态/下一期）

```
                    ┌─────────────────┐
                    │   Nginx (80)    │
                    │   /api → backend │
                    │   /   → frontend │
                    └─────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
        ┌──────────────┐      ┌──────────────┐
        │   Backend    │      │   Frontend   │
        │  (x3 Pods)   │      │  (Static)    │
        └──────────────┘      └──────────────┘
                │
        ┌───────┴────────┬─────────────┐
        ▼                ▼             ▼
    ┌─────────┐    ┌─────────┐   ┌─────────┐
    │PostgreSQL│   │ Milvus  │   │  MinIO  │
    │ (Primary)│   │ (Stand) │   │ (Shared)│
    └─────────┘    └─────────┘   └─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌─────────┐
│PostgreSQL│ │  Redis  │
│ (Replica)│ │ (Cache) │
└─────────┘ └─────────┘
```

---

## 八、性能优化

> 说明：本章中数据库/Redis相关优化属于下一期目标态。本期以功能正确与知识库可用为主。

### 8.1 数据库优化

- **索引优化**: 为常用查询字段建立索引
- **分页查询**: 所有列表接口支持分页
- **连接池**: 使用pgbouncer管理连接

### 8.2 缓存策略

- **Redis缓存**:
  - 用户信息缓存（1小时）
  - 任务详情缓存（10分钟）
  - 系统配置缓存（永久）

### 8.3 前端优化

- **代码分割**: React Lazy + Suspense
- **虚拟滚动**: 大数据量表格使用虚拟滚动
- **请求合并**: 批量操作合并请求

---

## 九、监控与日志

### 9.1 日志规范

```
[时间] [级别] [模块] [用户] [操作] [详细信息]
示例: 2025-01-28 10:00:00 INFO task zhangsan create_task 创建任务: xxx
```

### 9.2 监控指标

- **系统指标**: CPU、内存、磁盘、网络
- **应用指标**: QPS、响应时间、错误率
- **业务指标**: 任务数量、评估完成率、AI准确率

---

## 十、附录

### 10.1 术语表

| 术语 | 说明 |
|------|------|
| AI预估 | 系统自动生成的功能点人天估算 |
| 专家均值 | 3位专家评估结果的平均值 |
| 偏离度 | \|专家均值 - AI预估\| / AI预估 × 100% |
| 高偏离 | 偏离度超过20%的功能点 |
| 盲评 | 专家之间互不可见的评估方式 |
| 轮次 | 多轮评估中的一轮，最多3轮 |

### 10.2 状态码

| 代码 | 说明 |
|------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |
