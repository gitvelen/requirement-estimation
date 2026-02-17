# 业务需求工作量评估系统 - API接口文档

## 版本：v2.0.0
**最后更新**：2026-01-23
**基础URL**：`http://172.18.121.196:443/api/v1`

---

## 目录

1. [安全说明](#安全说明)
2. [通用响应格式](#通用响应格式)
3. [API接口](#api接口)
   - [需求评估](#需求评估)
   - [任务管理](#任务管理)
   - [人机协作修正](#人机协作修正)
   - [知识库管理](#知识库管理)
   - [子系统管理](#子系统管理)
   - [COSMIC配置](#cosmic配置)
   - [主系统管理](#主系统管理)
4. [错误码](#错误码)
5. [安全加固说明](#安全加固说明)

---

## 安全说明

### 访问控制

- **CORS限制**：仅允许配置的域名访问API
- **安全响应头**：所有响应包含安全HTTP头
- **文件验证**：上传文件经过MIME类型和大小验证
- **路径保护**：防止路径遍历攻击

### 安全响应头

| 响应头 | 说明 |
|-------|------|
| `X-Content-Type-Options` | 防止MIME类型嗅探 |
| `X-Frame-Options` | 防止点击劫持 |
| `X-XSS-Protection` | 启用XSS过滤器 |
| `Content-Security-Policy` | 内容安全策略 |
| `Referrer-Policy` | 引用来源策略 |
| `Permissions-Policy` | 权限策略 |

### 文件上传限制

| 限制项 | 说明 |
|-------|------|
| 文件类型 | 仅支持 `.docx` 格式 |
| 文件大小 | 最大 10MB |
| MIME验证 | 使用 python-magic 验证真实文件类型 |
| 路径验证 | 防止路径遍历攻击 |

---

## 通用响应格式

### 成功响应
```json
{
  "code": 200,
  "message": "操作成功",
  "data": { ... }
}
```

### 错误响应
```json
{
  "detail": "错误描述信息"
}
```

---

## API接口

### 需求评估

#### 1. 上传需求文档

**接口**：`POST /requirement/upload`

**请求参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 需求文档（.docx格式，最大10MB） |

**响应示例**：
```json
{
  "code": 200,
  "message": "文件上传成功",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "需求文档.docx",
    "status": "pending"
  }
}
```

**安全加固**：
- ✅ 文件名后缀验证
- ✅ 文件大小限制检查（10MB）
- ✅ MIME类型验证
- ✅ 文件内容验证

---

#### 2. DevOps评估接口

**接口**：`POST /requirement/evaluate`

**请求参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| request_id | string | 是 | 请求ID |
| file | File | 是 | 需求文档（.docx格式） |
| callback_url | string | 否 | 回调通知地址 |
| priority | int | 否 | 优先级（默认0） |

**响应示例**：
```json
{
  "code": 200,
  "message": "评估任务已创建",
  "data": {
    "task_id": "REQ-2024-TEST-001",
    "status": "pending"
  }
}
```

**安全加固**：
- ✅ 文件上传验证（同上传接口）
- ✅ 回调超时时间：120秒（适配异步任务）
- ✅ URL格式验证

---

### 任务管理

#### 3. 获取所有任务

**接口**：`GET /requirement/tasks`

**响应示例**：
```json
{
  "code": 200,
  "data": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "需求文档.docx",
      "status": "completed",
      "progress": 100,
      "message": "评估完成",
      "report_path": "data/报告_需求文档.xlsx",
      "created_at": "2026-01-21T10:30:00"
    }
  ],
  "total": 1
}
```

**任务状态**：
| 状态 | 说明 |
|------|------|
| `pending` | 待处理 |
| `processing` | 处理中 |
| `completed` | 已完成 |
| `failed` | 失败 |

---

#### 4. 获取任务状态

**接口**：`GET /requirement/status/{task_id}`

**路径参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务ID |

**响应示例**：
```json
{
  "code": 200,
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "progress": 65,
    "message": "正在拆分功能点...",
    "report_path": null,
    "error": null,
    "filename": "需求文档.docx",
    "created_at": "2026-01-21T10:30:00"
  }
}
```

---

#### 5. 下载报告

**接口**：`GET /requirement/report/{task_id}`

**路径参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务ID |

**响应**：Excel文件（application/vnd.openxmlformats-officedocument.spreadsheetml.sheet）

**安全加固**：
- ✅ 路径遍历防护（验证报告路径在data目录内）
- ✅ 任务状态验证（仅允许下载已完成的任务）
- ✅ 文件存在性检查

---

#### 6. 健康检查

**接口**：`GET /health`

**响应示例**：
```json
{
  "status": "healthy",
  "service": "业务需求工作量评估系统",
  "version": "1.0.0"
}
```

---

### 人机协作修正

#### 7. 获取评估结果

**接口**：`GET /requirement/result/{task_id}`

**路径参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务ID |

**响应示例**：
```json
{
  "code": 200,
  "data": {
    "task_id": "550e8400",
    "systems_data": {
      "新一代核心系统": [
        {
          "序号": "1.1",
          "功能模块": "账户管理",
          "功能点": "开立个人账户",
          "业务描述": "客户通过柜面/网银申请开立个人结算账户",
          "预估人天": 3,
          "复杂度": "中"
        }
      ]
    },
    "modifications": [],
    "confirmed": false
  }
}
```

**说明**：
- 获取AI评估的详细结果，包含所有系统的功能点数据
- 可用于在线编辑和修正

---

#### 8. 更新功能点

**接口**：`PUT /requirement/features/{task_id}`

**路径参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务ID |

**请求体**：
```json
{
  "system": "新一代核心系统",
  "operation": "update",
  "feature_index": 0,
  "feature_data": {
    "预估人天": 5
  }
}
```

**operation类型**：
| 操作 | 说明 |
|------|------|
| update | 修改功能点字段 |
| add | 添加新功能点 |
| delete | 删除功能点 |

**响应示例**：
```json
{
  "code": 200,
  "message": "更新成功",
  "data": {
    "operation": "update",
    "system": "新一代核心系统",
    "feature_index": 0
  }
}
```

---

#### 9. 确认评估

**接口**：`POST /requirement/confirm/{task_id}`

**路径参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务ID |

**响应示例**：
```json
{
  "code": 200,
  "message": "确认成功",
  "data": {
    "report_path": "data/xxx_最终报告_20260123_143022.xlsx",
    "confirmed_at": "2026-01-23T14:30:22"
  }
}
```

**说明**：
- 确认后生成最终报告（带"_final"后缀）
- 确认后无法继续编辑

---

#### 10. 获取修改历史

**接口**：`GET /requirement/modifications/{task_id}`

**路径参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务ID |

**响应示例**：
```json
{
  "code": 200,
  "data": {
    "task_id": "550e8400",
    "total": 2,
    "modifications": [
      {
        "id": "mod_001",
        "timestamp": "2026-01-23T14:25:00",
        "operation": "update",
        "system": "新一代核心系统",
        "field": "预估人天",
        "old_value": 3,
        "new_value": 5
      }
    ]
  }
}
```

---

### 知识库管理

#### 11. 导入知识

**接口**：`POST /knowledge/import`

**请求参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 系统知识文件（DOCX/PPTX） |
| system_name | string | 是 | 主系统名称（一个主系统一套知识库） |
| auto_extract | boolean | 否 | 是否自动提取（默认true） |

**响应示例**：
```json
{
  "code": 200,
  "message": "导入完成，成功48条，失败2条",
  "data": {
    "total": 50,
    "success": 48,
    "failed": 2,
    "errors": [...]
  }
}
```

**支持的文件格式**：
- DOCX：系统说明书、系统架构说明
- PPTX：系统架构汇报、系统介绍材料

---

#### 12. 检索知识

**接口**：`POST /knowledge/search`

**请求体**：
```json
{
  "query": "账户管理功能",
  "system_name": "支付中台",
  "top_k": 5,
  "similarity_threshold": 0.6
}
```

**响应示例**：
```json
{
  "code": 200,
  "data": {
    "total": 3,
    "results": [
      {
        "system_name": "支付中台",
        "knowledge_type": "system_profile",
        "similarity": 0.85,
        "metadata": {
          "system_name": "支付中台",
          "system_short_name": "Payment",
          "business_goal": "...",
          "core_functions": "...",
          "tech_stack": "..."
        }
      }
    ]
  }
}
```

---

#### 13. 获取知识库统计

**接口**：`GET /knowledge/stats`

**响应示例**：
```json
{
  "code": 200,
  "data": {
    "name": "system_knowledge",
    "count": 150,
    "index": "IVF_FLAT"
  }
}
```

---

#### 14. 知识库健康检查

**接口**：`GET /knowledge/health`

**响应示例**：
```json
{
  "code": 200,
  "status": "healthy",
  "service": "knowledge_base"
}
```

---

### 子系统管理

#### 7. 获取子系统映射

**接口**：`GET /subsystem/mappings`

**响应示例**：
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "total": 31,
    "items": [
      {
        "subsystem": "交易子系统",
        "mainSystem": "核心交易系统"
      }
    ]
  }
}
```

---

#### 8. 添加子系统映射

**接口**：`POST /subsystem/mappings`

**请求体**：
```json
{
  "subsystem": "交易子系统",
  "main_system": "核心交易系统"
}
```

**响应示例**：
```json
{
  "code": 200,
  "message": "添加成功",
  "data": {
    "subsystem": "交易子系统",
    "main_system": "核心交易系统"
  }
}
```

**安全加固**：
- ✅ 使用csv模块防止CSV注入
- ✅ 输入验证

---

#### 9. 更新子系统映射

**接口**：`PUT /subsystem/mappings/{subsystem}`

**路径参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| subsystem | string | 是 | 子系统名称 |

**请求体**：同添加接口

---

#### 10. 删除子系统映射

**接口**：`DELETE /subsystem/mappings/{subsystem}`

---

#### 11. 重新加载子系统映射

**接口**：`POST /subsystem/reload`

**说明**：热加载配置，无需重启服务

---

### COSMIC配置

#### 12. 获取COSMIC配置

**接口**：`GET /cosmic/config`

**响应示例**：
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "data_movements": {
      "E": { "name": "入口", "weight": 2 },
      "R": { "name": "读", "weight": 2 },
      "W": { "name": "写", "weight": 2 },
      "X": { "name": "出口", "weight": 1 }
    },
    "keywords": { ... }
  }
}
```

---

#### 13. 更新COSMIC配置

**接口**：`POST /cosmic/config`

**请求体**：
```json
{
  "data_movements": {
    "E": { "name": "入口", "weight": 2 }
  }
}
```

---

### 主系统管理

#### 14. 获取主系统列表

**接口**：`GET /system/systems`

**响应示例**：
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "total": 121,
    "systems": [
      {
        "name": "核心交易系统",
        "abbreviation": "CTS",
        "status": "运行中"
      }
    ]
  }
}
```

---

#### 15. 添加主系统

**接口**：`POST /system/systems`

**请求体**：
```json
{
  "name": "核心交易系统",
  "abbreviation": "CTS",
  "status": "运行中"
}
```

**安全加固**：
- ✅ 使用csv模块防止CSV注入
- ✅ 重复性检查

---

#### 16. 更新主系统

**接口**：`PUT /system/systems/{system_name}`

---

#### 17. 删除主系统

**接口**：`DELETE /system/systems/{system_name}`

---

#### 18. 重新加载主系统

**接口**：`POST /system/reload`

---

## 错误码

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 403 | 禁止访问（路径遍历攻击等） |
| 404 | 资源不存在 |
| 413 | 文件过大 |
| 500 | 服务器内部错误 |

---

## 安全加固说明

### 本次安全修复（2026-01-21）

| 问题 | 修复内容 | 影响 |
|------|---------|------|
| CORS完全开放 | 限制为配置的域名列表 | 防止CSRF攻击 |
| HTTP方法限制 | 仅允许GET/POST/PUT/DELETE | 减少攻击面 |
| 文件上传验证 | 添加MIME类型和大小检查 | 防止恶意文件上传 |
| 路径遍历漏洞 | 添加路径验证 | 防止访问任意文件 |
| CSV注入风险 | 使用csv模块处理CSV | 防止注入攻击 |
| LLM超时 | 调整为120秒 | 适配异步任务 |
| 前端XSS防护 | 添加DOMPurify库 | 防止XSS攻击 |
| 安全响应头 | 添加7种安全响应头 | 增强安全性 |
| 容器安全 | 前端使用非root用户 | 降低容器逃逸风险 |

### 前端安全工具

文件位置：`frontend/src/utils/security.js`

| 函数 | 说明 |
|------|------|
| `sanitizeHTML()` | 清理HTML内容 |
| `escapeHTML()` | 转义HTML特殊字符 |
| `isValidURL()` | 验证URL安全性 |
| `isValidFilename()` | 验证文件名安全性 |

---

## 配置说明

### 环境变量（.env）

```bash
# CORS配置
ALLOWED_ORIGINS=http://172.18.121.196,http://172.18.121.196:80

# LLM配置
DASHSCOPE_API_KEY=your_api_key_here
LLM_TIMEOUT=120  # 超时时间（秒）

# 应用配置
DEBUG=false
PORT=443

# 文件上传
MAX_FILE_SIZE=10485760  # 10MB
```

---

## 部署说明

### 安装新依赖

```bash
# 后端依赖
cd /home/admin/Claude/requirement-estimation-system
pip install python-magic

# 前端依赖
cd frontend
npm install dompurify
```

### 重启服务

```bash
# 停止服务
pkill -f "python3 backend/app.py"
pkill -f "react-scripts start"

# 启动后端
nohup python3 backend/app.py > logs/backend.log 2>&1 &

# 启动前端
cd frontend && nohup sh -c 'BROWSER=none HOST=0.0.0.0 PORT=80 npm start' > ../logs/frontend.log 2>&1 &
```

---

## 联系方式

**系统名称**：业务需求工作量评估系统
**版本**：v1.0.0
**文档更新**：2026-01-21
