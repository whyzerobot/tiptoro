# TipToro 🎯

智能错题分析系统 — 帮助初高中学生扫描、归类、分析错题，提供个性化学习建议。

## 项目结构

```
tiptoro/
├── backend/          ← Python FastAPI 后端
│   ├── config/       ← 统一配置 (settings.yaml + .env)
│   ├── gateway/      ← Orchestrator + Skill 调度引擎
│   ├── skills/       ← 原子化 AI 技能插件
│   ├── llm/          ← 多 LLM 适配器（DeepSeek/Gemini/OpenAI）
│   ├── infra/        ← 数据库 + 对象存储 (SQLite→PostgreSQL, 本地→OSS)
│   ├── auth/         ← 用户认证（邮箱注册/JWT）
│   ├── users/        ← 用户空间（soul.md / user.md + AI 上下文注入）
│   └── api/          ← FastAPI HTTP 路由（待实现）
│
├── frontend/         ← React/Vite 前端（待实现）
├── shared/           ← API 类型契约（OpenAPI → TypeScript）
└── docs/             ← 产品文档 (PRD.md / Architecture.md)
```

## 快速开始（本地开发）

```bash
# 1. 克隆项目
git clone <repo-url> && cd tiptoro

# 2. 安装后端依赖
pip install -r backend/requirements.txt

# 3. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，至少设置 JWT_SECRET

# 4. 初始化数据库（SQLite，无需额外安装）
cd backend && python3 -c "from infra import models; from infra.database import init_db; init_db()"

# 5. 启动后端（API 实现后）
cd tiptoro && python3 -m backend
```

## 环境切换

| 场景 | 配置 |
|------|------|
| 本地开发 | `.env` → `TIPTORO_ENV=local`（SQLite + 本地文件存储） |
| 云端部署 | `.env` → `TIPTORO_ENV=cloud`（PostgreSQL + 阿里云 OSS） |

详细配置说明见 [`backend/config/settings.yaml`](backend/config/settings.yaml)。
