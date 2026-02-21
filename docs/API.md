# TipToro 后端 API 参考文档

> **当前状态**：后端核心模块已实现，FastAPI HTTP 路由层待开发。  
> 本文档描述**后端对前端提供的能力边界**，作为 API 设计的契约依据。

---

## 模块总览

| 模块 | 路径 | 主要能力 |
|------|------|----------|
| 认证 | `backend/auth/` | 注册、邮箱验证、登录、JWT |
| 用户空间 | `backend/users/` | soul.md / user.md 读写 |
| 计费 | `backend/billing/` | 激活码验证、订阅状态查询 |
| 错题处理 | `backend/gateway/` | Pipeline 编排、Skill 调度 |
| 大模型 | `backend/llm/` | 统一 LLM 调用（多 provider） |
| 基础设施 | `backend/infra/` | 数据库、对象存储 |

---

## 1. 认证模块 `/auth`

### POST `/auth/register`
注册新用户（邮箱 + 密码）。注册成功后自动发送验证邮件。

**Request Body**
```json
{
  "email": "student@example.com",
  "password": "MySecurePass123",
  "display_name": "张三"
}
```

**Response**
```json
{
  "success": true,
  "user_id": 42,
  "message": "注册成功！请查收验证邮件。"
}
```

**后端实现**：`auth.service.register()`  
**本地行为**：验证 token 打印到控制台，不发真实邮件。

---

### POST `/auth/verify-email`
用邮箱验证 token 完成邮箱验证。

**Request Body**
```json
{ "token": "abc123..." }
```

**Response**
```json
{ "success": true, "message": "邮箱验证成功！" }
```

**后端实现**：`auth.service.verify_email()`

---

### POST `/auth/login`
登录，返回 JWT access token（7 天有效）。

**Request Body**
```json
{
  "email": "student@example.com",
  "password": "MySecurePass123"
}
```

**Response**
```json
{
  "success": true,
  "access_token": "eyJhbGciOi...",
  "user_id": 42,
  "email": "student@example.com"
}
```

**后端实现**：`auth.service.login()` + `auth.jwt.create_access_token()`

---

### 🔮 Phase 2（预留接口）
| 端点 | 说明 |
|------|------|
| `POST /auth/login/phone` | 手机号 + 验证码登录 |
| `POST /auth/login/wechat` | 微信 OAuth 登录 |

---

## 2. 用户模块 `/users`

> 所有接口需要 `Authorization: Bearer <token>` header。

### GET `/users/me`
获取当前用户基本信息。

**Response**
```json
{
  "user_id": 42,
  "email": "student@example.com",
  "display_name": "张三",
  "avatar_url": null,
  "email_verified": true
}
```

---

### GET `/users/me/space/soul`
获取用户的 soul.md（AI 属性定义）。

**Response**
```json
{
  "content": "# Soul Configuration\n你是 TipToro 的专属学习助手..."
}
```

**后端实现**：`users.space.read_soul(user_id)`

---

### PUT `/users/me/space/soul`
更新 soul.md。

**Request Body**
```json
{ "content": "# Soul Configuration\n..." }
```

---

### GET/PUT `/users/me/space/profile`
读写 user.md（学生自我简介：年级、学科偏好、学习风格等）。

**后端实现**：`users.space.read_user_profile_md()` / `write_user_profile_md()`

---

> **AI 上下文注入机制**  
> 每次调用大模型时，系统自动读取 `soul.md + user.md` 拼接为 System Prompt 前缀：
> ```python
> from users.context import inject_user_context
> system = inject_user_context(user_id, base_system_prompt)
> ```

---

## 3. 计费模块 `/billing`

### POST `/billing/activate`
激活码兑换订阅。

**Request Body**
```json
{ "key": "bW9udGhseXwyMDI2LTAyLTIx..." }
```

**Response**
```json
{
  "success": true,
  "plan_id": "monthly",
  "plan_name": "月度会员",
  "expires_at": "2026-03-21T13:42:00Z",
  "days_remaining": 30,
  "mistakes_limit": null,
  "message": "月度会员，剩余 30 天"
}
```

**后端实现**：`billing.subscription.activate_key()`

---

### GET `/billing/status`
查询当前订阅状态和配额使用情况。

**Response**
```json
{
  "active": true,
  "plan_id": "trial",
  "plan_name": "试用版",
  "expires_at": "2026-02-28T00:00:00Z",
  "days_remaining": 6,
  "mistakes_used": 8,
  "mistakes_limit": 20,
  "can_add_mistake": true
}
```

**后端实现**：`billing.subscription.get_status()`

---

### 套餐说明

| 套餐 | 价格 | 有效期 | 错题配额 |
|------|------|--------|----------|
| trial | ¥9.90 | 7 天 | 最多 20 道 |
| monthly | ¥49.00 | 30 天 | 无限制 |
| annual | ¥399.00 | 365 天 | 无限制 |

### 激活码生成（管理员 CLI）
```bash
cd tiptoro
export BILLING_SECRET="your-secret"
python3 backend/billing/keygen_standalone.py --plan monthly --count 5
```

### 🔮 Phase 2（支付预留接口）
| 端点 | 说明 |
|------|------|
| `POST /billing/pay/wechat` | 创建微信支付订单 |
| `POST /billing/pay/alipay` | 创建支付宝订单 |
| `POST /billing/webhook/wechat` | 微信支付回调通知 |
| `POST /billing/webhook/alipay` | 支付宝回调通知 |

---

## 4. 错题模块 `/mistakes`

> 以下端点封装 Gateway Orchestrator Pipeline。

### POST `/mistakes/upload`
上传一张错题图片，启动 AI 处理 Pipeline。

**Request**：`multipart/form-data` 含 `image` 字段

**Response**（立即返回，异步处理）
```json
{
  "task_id": "uuid-1234",
  "status": "pending",
  "message": "已提交处理，请稍候查询状态"
}
```

**后端流程**：
```
图片 → OSS 存储 → vision-perception Skill → status=awaiting_human
```

---

### GET `/mistakes/tasks/{task_id}`
查询任务状态。

**Response**
```json
{
  "task_id": "uuid-1234",
  "status": "awaiting_human",
  "ocr_result": {
    "question_text": "已识别的题目文本（含 LaTeX）",
    "wrong_answer_text": "学生手写错答识别文本"
  }
}
```

---

### POST `/mistakes/tasks/{task_id}/verify`
前端人工校对完成后提交，继续 Pipeline。

**Request Body**
```json
{
  "question_text": "（校对后的题目文本）",
  "wrong_answer_text": "（校对后的错答文本）",
  "subject": "math",
  "error_reason": "concept_unclear"
}
```

**后端流程**：
```
校对数据 → ingest-and-verify Skill → cognitive-analysis Skill → status=completed
```

---

### GET `/mistakes`
获取用户错题列表（分页 + 筛选）。

**Query Params**：`subject`, `error_reason`, `page`, `page_size`

**Response**
```json
{
  "total": 42,
  "items": [
    {
      "record_id": 1,
      "question_text": "...",
      "subject": "math",
      "knowledge_nodes": ["函数", "一次函数"],
      "error_reason": "concept_unclear",
      "created_at": "2026-02-21T13:00:00Z"
    }
  ]
}
```

---

### GET `/mistakes/{record_id}/analysis`
获取单道错题的 AI 分析结果。

**Response**
```json
{
  "record_id": 1,
  "knowledge_nodes": ["函数", "一次函数斜率"],
  "analysis_summary": "学生对斜率概念理解不足，混淆了...",
  "similar_keywords": ["斜率", "率变化", "线性函数"]
}
```

---

## 5. 学情分析模块 `/analytics`

### GET `/analytics/overview`
获取学生整体薄弱知识点分布（用于前端雷达图）。

**Response**
```json
{
  "subjects": {
    "math": {
      "total_mistakes": 18,
      "weak_nodes": ["几何", "三角函数"],
      "mastery_score": 62
    }
  }
}
```

---

### GET `/analytics/report`
生成并下载学情报告 PDF。

**后端实现**：`report-generation` Skill

---

## 6. LLM 路由说明（内部）

前端**不直接**调用 LLM，由后端各 Skill 内部调用统一接口：

```python
from llm import llm_call, Message
from users.context import inject_user_context

system = inject_user_context(user_id, "你是一位数学老师...")
response = llm_call(
    role="cognitive_analysis",   # 路由配置在 config/settings.yaml
    messages=[
        Message(role="system", content=system),
        Message(role="user", content=question),
    ],
    json_mode=True,
)
```

**支持的 LLM Provider（配置文件 `backend/config/settings.yaml`）**：
DeepSeek · Gemini · OpenAI · Grok · MiniMax

---

## 7. 通用约定

### 认证
所有需要鉴权的接口均在 Header 中携带：
```
Authorization: Bearer <jwt_token>
```

### 错误格式
```json
{
  "error": "INVALID_TOKEN",
  "message": "Token 已过期，请重新登录",
  "code": 401
}
```

### 订阅校验
新增错题类接口在入口处校验：
```python
can_add, reason = billing.subscription.check_can_add_mistake(user_id)
if not can_add:
    return 403, reason
```

---

*文档生成时间：2026-02-21 | 版本：v0.2-alpha*
