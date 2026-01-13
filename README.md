# 业务需求工作量评估系统

基于Agent智能体的业务需求工作量评估系统，核心流程为「接收需求说明书→解析核心内容→功能点拆分→工作量估算→输出Excel报告」。

## 功能特性

✅ 自动解析需求文档（.docx格式）
✅ 智能识别涉及系统
✅ 按系统维度拆分功能点
✅ Delphi专家评估法估算工作量
✅ 生成专业Excel评估报告
✅ RESTful API接口
✅ Web管理界面

## 技术架构

### 后端
- Python 3.11+
- FastAPI（API框架）
- LangChain/LangGraph（Agent框架）
- LlamaIndex（文档处理）
- OpenAI SDK（兼容阿里云DashScope）

### 前端
- React 18
- Ant Design
- Axios

### 智能体
- 文档解析Agent
- 系统识别Agent
- 功能点拆分Agent
- 工作量估算Agent
- 报告生成Agent

## 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- 阿里云DashScope API Key

### 安装

1. 克隆项目
```bash
git clone <repository-url>
cd requirement-estimation-system
```

2. 安装后端依赖
```bash
cd backend
pip install -r requirements.txt
```

3. 安装前端依赖
```bash
cd frontend
npm install
```

4. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，填入阿里云API Key
```

### 启动服务

1. 启动后端
```bash
cd backend
uv app:app --host 0.0.0.0 --port 8000
```

2. 启动前端
```bash
cd frontend
npm start
```

3. 访问系统
- 前端地址: http://localhost:3000
- API文档: http://localhost:8000/docs

## 使用说明

### API调用示例

```python
import requests

# 上传需求文档
url = "http://localhost:8000/api/v1/requirement/upload"
files = {"file": open("需求文档.docx", "rb")}
response = requests.post(url, files=files)
task_id = response.json()["data"]["task_id"]

# 查询任务状态
status_url = f"http://localhost:8000/api/v1/requirement/status/{task_id}"
response = requests.get(status_url)
print(response.json())

# 下载报告
report_url = f"http://localhost:8000/api/v1/requirement/report/{task_id}"
response = requests.get(report_url)
with open("评估报告.xlsx", "wb") as f:
    f.write(response.content)
```

## 项目结构

```
requirement-estimation-system/
├── backend/                # 后端代码
│   ├── api/               # API接口层
│   ├── agent/             # Agent智能体层
│   ├── service/           # 业务逻辑层
│   ├── utils/             # 工具层
│   ├── config/            # 配置层
│   ├── prompts/           # 提示词模板
│   ├── app.py             # 主程序
│   └── requirements.txt   # Python依赖
├── frontend/              # 前端代码
│   ├── src/
│   │   ├── pages/         # 页面组件
│   │   ├── components/    # 业务组件
│   │   └── services/      # API服务
│   └── package.json       # Node依赖
├── docs/                  # 文档
├── tests/                 # 测试用例
└── deploy/                # 部署配置
```

## 文档

详细文档请查看 `docs/` 目录：
- 项目说明.md
- 接口文档.md
- 开发手册.md
- 部署手册.md
- 测试用例.md

## 许可证

MIT License
