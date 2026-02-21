---
name: cognitive-analysis
description: 调用 LLM 对入库后的错题进行深度认知分析，提取知识点树节点、生成错因解析文本和举一反三搜索关键词，并将结果回写数据库。
---

# Skill: cognitive-analysis

## 职责
利用大语言模型（DeepSeek / Claude）作为智能引擎，完成对一道错题的三项认知输出：
1. **知识点挂载**：将题目挂载到初高中知识树的对应节点（可以是多个叶节点）。
2. **错因深度解析**：结合题干和学生错答，分析具体的错误逻辑，输出给学生看的分析文本。
3. **变式题关键词**：生成用于后续搜索相似题的考点关键词组。

## Input Schema
```json
{
  "task_id": "string",
  "record_id": "integer",
  "question_id": "integer",
  "question_text": "string (题干, 含 LaTeX)",
  "answer_text": "string  (学生错答, 含 LaTeX)",
  "subject": "string",
  "grade": "string",
  "error_reason": "string"
}
```

## Output Schema
```json
{
  "task_id": "string",
  "record_id": "integer",
  "status": "success | failed",
  "knowledge_nodes": ["string"] ,
  "analysis_summary": "string (面向学生的中文错因解析, 200字以内)",
  "similar_question_keywords": ["string"],
  "error": "string | null"
}
```

## 执行步骤

1. 调用 `scripts/prompt_builder.py`，根据 subject / grade / error_reason 组装 System Prompt 和 User Prompt。
2. 调用 **统一 LLM 接口** `llm.llm_call(role="cognitive_analysis", messages=[...], json_mode=True)`。
   模型路由由 `llm/config.yaml` 中的 `roles.cognitive_analysis` 决定，无需在此 Skill 中硬编码任何 provider 或 model。
3. 解析 LLM 返回的 JSON，校验 `knowledge_nodes` 是否属于合法的知识树节点（查询 `KnowledgeTag` 表校验枚举）。
4. 将 `knowledge_nodes`、`analysis_summary`、`similar_question_keywords` 回写到 `User_Mistake_Record` 表对应的 `record_id`。
5. 返回 Output Schema 标准 JSON。

## Prompt 设计要点
- System Prompt 中嵌入完整的学科知识树列表（从数据库动态读取），要求 LLM 只从其中选择节点，禁止自由发挥。
- 开启 `json_mode=True` 确保结构化输出，降低解析失败概率。
- 在全局 `llm/config.yaml` 中设置 `generation_defaults.temperature: 0.2` 保证输出稳定性。

## 错误处理
- LLM 返回非法 JSON 时，最多重试 2 次（由 provider 适配器内部处理），失败后 `status` 置 `failed`。
- `knowledge_nodes` 中若包含数据库中不存在的节点，自动过滤并记录日志，不阻断流程。

## 依赖
- `scripts/prompt_builder.py`
- `scripts/db_writer.py`
- `llm` 模块（`from llm import llm_call, Message`）— 通过 `llm/config.yaml` 配置路由到具体 provider
- 外部服务：PostgreSQL
