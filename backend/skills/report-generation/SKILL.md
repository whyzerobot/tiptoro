---
name: report-generation
description: 汇总某学生指定时间范围内的错题分析数据，生成可视化雷达图数据（JSON）和可打印的 PDF 错题本导出文件。
---

# Skill: report-generation

## 职责
作为系统最终的"结果呈现"环节，从数据库聚合用户的学情数据，输出两种形式的报告：
1. **学情看板数据**（JSON）：供前端渲染雷达图、折线图、错误频次热力图使用。
2. **PDF 错题本**：可直接用于打印，包含题目、学生的错答、参考答案和 AI 分析。

## Input Schema
```json
{
  "user_id": "string",
  "mode": "dashboard | pdf",
  "time_range": {
    "start": "string (ISO 8601, e.g. 2025-01-01)",
    "end": "string (ISO 8601)"
  },
  "record_ids": ["integer"] 
}
```
> `time_range` 和 `record_ids` 二选一：前者按时间范围聚合全部错题，后者按指定错题子集生成。

## Output Schema — Dashboard Mode
```json
{
  "user_id": "string",
  "status": "success | failed",
  "summary": {
    "total_mistakes": "integer",
    "subjects_breakdown": { "math": 12, "physics": 5 },
    "error_reason_breakdown": { "careless": 8, "concept_unclear": 6 }
  },
  "radar_chart_data": { "代数": 72, "几何": 44, "函数": 85 },
  "weakness_report": ["string (高频薄弱知识点描述)"],
  "error": "string | null"
}
```

## Output Schema — PDF Mode
```json
{
  "user_id": "string",
  "status": "success | failed",
  "pdf_url": "string (OSS URL, 有效期 7 天)",
  "page_count": "integer",
  "error": "string | null"
}
```

## 执行步骤

### Dashboard 模式
1. 调用 `scripts/aggregator.py` 按 `time_range` 或 `record_ids` 从 `User_Mistake_Record` JOIN `KnowledgeTag` 聚合数据。
2. 计算各知识树节点的错误频次，归一化为百分制掌握度（100 - 错误率 × 100）。
3. 返回结构化 JSON。

### PDF 模式
1. 调用 `scripts/aggregator.py` 获取指定错题详情列表（按错题本顺序排序）。
2. 调用 `scripts/pdf_renderer.py`，使用 WeasyPrint 或 Playwright 将 HTML 模版渲染为 PDF，支持 LaTeX 公式（通过 KaTeX 渲染）。
3. 上传 PDF 到 OSS，返回有时效的签名 URL。

## 错误处理
- 指定范围内无错题时，返回 `status: success` 但所有数值为 0，不视为错误。
- PDF 渲染失败时 `status` 置 `failed`，保存中间 HTML 到临时目录便于 debug。

## 依赖
- `scripts/aggregator.py`
- `scripts/pdf_renderer.py`
- 外部服务：PostgreSQL、OSS
