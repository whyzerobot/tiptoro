# 系统架构设计 — TipToro

> 版本：v0.2-alpha（2026-02-21）  
> 实现状态：后端核心模块已完成，FastAPI 路由层和前端待开发。

---

## 1. 整体目录结构

```
tiptoro/
├── backend/                    ← Python 后端（FastAPI）
│   ├── config/
│   │   ├── settings.yaml       ← 唯一非密配置（env 切换、LLM 路由）
│   │   └── loader.py           ← AppSettings 统一加载器
│   │
│   ├── api/                    ← FastAPI 路由层（待开发）
│   │
│   ├── gateway/                ← Orchestrator + Skill 调度引擎
│   │   ├── loader.py           ← SkillRegistry（扫描 skills/ 目录）
│   │   ├── context.py          ← TaskContext（跨 Skill 数据容器）
│   │   └── orchestrator.py     ← Pipeline 编排、暂停/续跑
│   │
│   ├── skills/                 ← 原子化 AI 功能插件
│   │   ├── vision-perception/  ← OCR + 手写识别
│   │   ├── ingest-and-verify/  ← 去重 + 入库
│   │   ├── cognitive-analysis/ ← LLM 知识点分析
│   │   └── report-generation/  ← 学情报告生成
│   │
│   ├── llm/                    ← 多模型统一适配层
│   │   ├── client.py           ← llm_call() 统一入口
│   │   └── providers/          ← DeepSeek/Gemini/OpenAI/Grok/MiniMax
│   │
│   ├── auth/                   ← 用户认证
│   │   ├── service.py          ← register / login / verify_email
│   │   ├── jwt.py              ← JWT 签发/验证
│   │   ├── password.py         ← bcrypt 哈希
│   │   └── email.py            ← 邮件服务（local 打印 / cloud SMTP）
│   │
│   ├── users/                  ← 用户个人空间
│   │   ├── space.py            ← soul.md / user.md 读写
│   │   └── context.py          ← AI 上下文构建器（注入 LLM System Prompt）
│   │
│   ├── billing/                ← 计费与订阅
│   │   ├── plans.py            ← 套餐定义（trial/monthly/annual）
│   │   ├── keys.py             ← HMAC 激活码生成/验证
│   │   ├── subscription.py     ← 激活 / 状态查询 / 配额检查
│   │   ├── keygen_standalone.py← CLI 激活码生成工具
│   │   └── payment/            ← 支付渠道（微信/支付宝 stub 预留）
│   │
│   ├── infra/                  ← 基础设施层
│   │   ├── config.py           ← InfraConfig 薄包装（委托 AppSettings）
│   │   ├── database.py         ← SQLAlchemy Engine / Session / init_db
│   │   ├── models.py           ← ORM 模型（User/Question/Subscription 等）
│   │   └── storage.py          ← 统一存储客户端（Local/OSS/S3）
│   │
│   └── .env.example            ← 所有密钥模版
│
├── frontend/                   ← React/Vite 前端（待开发）
├── shared/                     ← API 类型契约（OpenAPI → TypeScript）
└── docs/                       ← 产品与技术文档
```

---

## 2. 核心设计：Orchestrator + Skills

```
[HTTP 请求] → [FastAPI 路由] → [Orchestrator.run(ctx)]
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
             vision-perception   ingest-and-verify  cognitive-analysis
             (OCR + 手写识别)    (去重 + 入库)      (LLM 知识点分析)
                    │
                ⏸ await_human
                    │
             [前端人工校对] → resume_after
```

### Pipeline 编排（代码示例）
```python
from gateway import registry, TaskContext, build_default_pipeline

registry.load_all()
pipeline = build_default_pipeline()

# 阶段 1：OCR → 暂停等待校对
ctx = TaskContext(user_id=42, image_source="storage://raw/user_42/q1.jpg")
ctx = await pipeline.run(ctx)
# → ctx.status == AWAITING_HUMAN

# 阶段 2：校对完成 → 继续入库 + 分析
ctx.verified_question_text = "..."
ctx.wrong_answer_text = "..."
ctx = await pipeline.run(ctx, resume_after="vision-perception")
# → ctx.status == COMPLETED
```

---

## 3. 配置与环境切换

| 文件 | 职责 |
|------|------|
| `backend/config/settings.yaml` | 行为配置（路由/套餐/连接参数），提交 git |
| `backend/.env` | 所有密钥（不提交 git） |

```bash
# 切换环境（一行命令）
export TIPTORO_ENV=local   # SQLite + 本地文件系统
export TIPTORO_ENV=cloud   # PostgreSQL + 阿里云 OSS
```

---

## 4. LLM 路由

所有 Skill 通过统一入口调用大模型，路由配置在 `settings.yaml`：

```python
from llm import llm_call, Message
from users.context import inject_user_context

system = inject_user_context(user_id, "你是一位数学老师...")  # 注入用户个性化上下文
resp = llm_call(role="cognitive_analysis", messages=[...], json_mode=True)
```

| 角色 | Provider | 模型 |
|------|----------|------|
| cognitive_analysis | DeepSeek | deepseek-chat |
| text_cleanup | Gemini | gemini-2.0-flash |
| report_writing | DeepSeek | deepseek-chat |
| fallback | OpenAI | gpt-4o-mini |

---

## 5. 数据库表结构

| 表名 | 说明 |
|------|------|
| `users` | 用户账户（邮箱、密码哈希、认证状态） |
| `auth_providers` | 第三方登录预留（email/phone/wechat） |
| `email_verification_tokens` | 邮箱验证令牌 |
| `user_profiles` | 用户年级、学科偏好等结构化属性 |
| `question_tasks` | 每次上传的处理任务（生命周期追踪） |
| `questions` | 去重后的干净题目库 |
| `user_mistake_records` | 学生错题记录（含 AI 分析结果） |
| `knowledge_tags` | 知识点标签树 |
| `subscriptions` | 用户订阅记录 |
| `activation_keys` | 激活码使用审计 |

---

## 6. 技术栈

| 层级 | 选型 |
|------|------|
| 后端框架 | Python 3.11 + FastAPI |
| 数据库（本地） | SQLite + SQLAlchemy |
| 数据库（云端） | PostgreSQL + SQLAlchemy |
| 对象存储（本地） | 本地文件系统 |
| 对象存储（云端） | 阿里云 OSS（可切换 AWS S3） |
| 异步任务 | Celery + Redis（待接入） |
| 前端 | React + Vite（待开发） |
| OCR | Mathpix（印刷体）+ 百度手写 OCR |
| LLM | DeepSeek / Gemini / OpenAI / Grok / MiniMax |
| 认证 | JWT（PyJWT）+ bcrypt |
| 计费 | HMAC 激活码；微信支付/支付宝（Phase 2） |
