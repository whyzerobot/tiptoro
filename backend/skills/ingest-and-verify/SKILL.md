---
name: ingest-and-verify
description: 接受经前端人工校对确认后的结构化数据，执行去重检测并写入核心数据库（Question 表和 User_Mistake_Record 表）。
---

# Skill: ingest-and-verify

## 职责
作为数据入库的唯一官方入口，保证写入数据库的内容是**已经过人工确认的高质量数据**。处理题目去重逻辑，关联知识点标签初始化（空标签，等待 cognitive-analysis 填充）。

## Input Schema
```json
{
  "task_id": "string",
  "user_id": "string",
  "verified_question_text": "string (人工校对后的题干文本, 含 LaTeX)",
  "verified_answer_text": "string  (人工校对后的错答文本)",
  "clean_question_image_url": "string",
  "handwritten_answer_image_url": "string",
  "subject": "math | physics | chemistry | biology | history | geography | politics | english | chinese",
  "grade": "junior_1 | junior_2 | junior_3 | high_1 | high_2 | high_3",
  "error_reason": "careless | concept_unclear | formula_wrong | no_idea | other"
}
```

## Output Schema
```json
{
  "task_id": "string",
  "status": "success | failed",
  "question_id": "integer",
  "record_id": "integer",
  "is_duplicate_question": "boolean (若题目已存在则复用旧 question_id)",
  "error": "string | null"
}
```

## 执行步骤

1. 调用 `scripts/dedup.py`：对 `verified_question_text` 做 SHA256 哈希，查询 Question 表是否已存在相同哈希的题目。
2. **若无重复**：INSERT 一条新记录到 `Question` 表，获得 `question_id`。
3. **若已存在**：复用现有 `question_id`，`is_duplicate_question` 置 `true`。
4. INSERT 一条新记录到 `User_Mistake_Record` 表，关联 `user_id` 和 `question_id`，获得 `record_id`。
5. 初始化该记录的 `knowledge_tags` 字段为空数组（等待 `cognitive-analysis` 异步填充）。
6. 返回 Output Schema 标准 JSON。

## 错误处理
- 数据库写入失败时立即回滚，`status` 置 `failed` 并填写 `error` 字段。
- `subject` / `grade` 校验失败时（非合法枚举值）拒绝写入。

## 依赖
- `scripts/dedup.py`
- `scripts/db_writer.py`
- 外部服务：PostgreSQL
