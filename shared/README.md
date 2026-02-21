# shared/

前后端共享的接口契约、类型定义和 API 文档。

## 目录结构（按需创建）

```
shared/
├── openapi.yaml        ← FastAPI 自动生成（运行后端后导出）
├── api-types/
│   └── index.d.ts      ← 由 openapi-typescript 从 openapi.yaml 生成的 TS 类型
└── constants/
    └── error_codes.py  ← Python 错误码（前后端同步使用）
```

## 生成 TS 类型（待后端 API 实现后）

```bash
# 1. 启动后端，导出 OpenAPI schema
curl http://localhost:8000/openapi.json -o shared/openapi.yaml

# 2. 生成 TypeScript 类型
npx openapi-typescript shared/openapi.yaml -o shared/api-types/index.d.ts
```
