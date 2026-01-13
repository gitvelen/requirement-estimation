# 快速启动指南

## 🚀 5分钟快速上手

### 第一步：准备环境（2分钟）

```bash
# 1. 检查Python版本
python --version  # 需要 3.11+

# 2. 进入项目目录
cd "D:\Program Files\node-v24.12.0-win-x64\.claude\ccep\requirement-estimation-system"

# 3. 安装后端依赖
cd backend
pip install -r requirements.txt

# 4. 配置阿里云API Key
cp ../.env.example ../.env
# 编辑.env文件，填入你的DASHSCOPE_API_KEY
```

### 第二步：启动服务（1分钟）

```bash
# 启动后端（在backend目录）
uv app:app --host 0.0.0.0 --port 8000
```

看到以下输出表示启动成功：
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 第三步：测试接口（2分钟）

打开新的终端窗口，执行：

```bash
# 测试健康检查
curl http://localhost:8000/api/v1/health

# 上传测试文档（如果有.docx文档）
curl -X POST "http://localhost:8000/api/v1/requirement/upload" \
  -F "file=@测试需求.docx"
```

### 完成！

🎉 访问 http://localhost:8000/docs 查看API文档

---

## 📚 详细文档

| 文档 | 说明 |
|------|------|
| PROJECT_OVERVIEW.md | 项目总览（推荐先看这个） |
| docs/项目说明.md | 详细项目说明 |
| docs/接口文档.md | API接口文档 |
| docs/开发手册.md | 开发指南 |
| docs/部署手册.md | 部署指南 |

---

## ❓ 常见问题

**Q: 没有uv命令怎么办？**

```bash
pip install uv
```

**Q: 如何获取阿里云API Key？**

访问：https://dashscope.console.aliyun.com/

**Q: 如何集成到现有系统？**

参考 `docs/接口文档.md` 中的DevOps集成示例

---

## 🎯 核心功能

✅ 自动解析需求文档（.docx）
✅ 智能识别涉及系统
✅ 按系统维度拆分功能点
✅ Delphi专家评估法估算工作量
✅ 生成Excel评估报告
✅ RESTful API接口

---

## 📞 获取帮助

1. 查看 PROJECT_OVERVIEW.md
2. 查看 docs 目录下的文档
3. 查看 logs/app.log 日志文件

---

**祝你使用愉快！**
