---
name: vision-perception
description: 对上传的错题原图执行版面分析、印刷体/手写体分区识别和笔迹擦除。输出干净的题干图片、手写错答切片和对应的 OCR 文本（含 LaTeX 公式）。
---

# Skill: vision-perception

## 职责
接受一张原始错题图片，完成以下三个原子操作并输出结构化结果：
1. **版面分析**：定位印刷题干区域和手写答题区域的边界 bounding box。
2. **OCR 提取**：对印刷区域调用数学公式 OCR（Mathpix / 百度教育版），返回含 LaTeX 的 Markdown 文本；对手写区域调用手写 OCR，返回手写文本。
3. **图层分离**：利用图像 Inpainting 将手写笔迹擦除，生成干净的题干底图；同时裁出手写区域截图单独保存。

## Input Schema
```json
{
  "task_id": "string (uuid)",
  "image_source": "string (OSS URL or base64 data URI)",
  "user_id": "string"
}
```

## Output Schema
```json
{
  "task_id": "string",
  "status": "success | partial | failed",
  "clean_question_image_url": "string (OSS URL, 去手写的干净题干图)",
  "handwritten_answer_image_url": "string (OSS URL, 手写区域截图)",
  "raw_question_text": "string (印刷区域 OCR 文本, 含 LaTeX)",
  "raw_answer_text": "string  (手写区域 OCR 文本)",
  "confidence": {
    "question_ocr": "float [0,1]",
    "answer_ocr": "float [0,1]"
  },
  "error": "string | null"
}
```

## 执行步骤

1. 调用 `scripts/preprocess.py` 对图片进行透视矫正和去噪处理。
2. 调用 `scripts/layout_detect.py` 获取印刷区域和手写区域的 bounding box 列表。
3. 对印刷区域调用 OCR 适配器（见 `scripts/ocr_adapter.py`），得到含公式的 Markdown 文本。
4. 对手写区域调用手写 OCR 适配器（支持百度/讯飞），得到手写答案文本。
5. 调用 `scripts/inpaint.py` 擦除原图中的手写内容，保存清洁版底图到 OSS。
6. 裁剪手写区域图片，单独上传 OSS。
7. 返回 Output Schema 标准 JSON。

## 错误处理
- OCR 返回置信度 < 0.6 时，`status` 字段设为 `partial`，前端需强制触发人工校对流程。
- 网络调用超时重试 3 次，全部失败时 `status` 置 `failed` 并填写 `error` 字段。

## 依赖
- `scripts/preprocess.py`
- `scripts/layout_detect.py`
- `scripts/ocr_adapter.py`
- `scripts/inpaint.py`
- 外部服务：OSS (对象存储)、OCR API（百度 / Mathpix）
