# Repository Guidelines

## 项目结构与模块组织

当前仓库包含 OneMate 血常规报告解读智能体的需求与样例数据：

- `requirement.md`：任务背景、架构约束与交付节奏。
- `tasks/prd-blood-report-interpreter.md`：完整 PRD、验收标准、API 与组件设计。
- `blood_testcase.json`：血常规 JSON 输入样例，用于前后端校验与测试。

实现阶段建议保持 B/S 架构：前端放在 `frontend/`（Vue 3 + Vite），后端放在 `backend/`（FastAPI + 内存 DB），测试分别放在 `frontend/src/**/__tests__/` 与 `backend/tests/`。静态资源放在 `frontend/src/assets/`，共享示例或 fixtures 可放在 `tests/fixtures/`。

## 构建、测试与本地开发命令

仓库目前尚未包含脚手架与包管理配置。新增实现后请在各模块提供明确脚本，例如：

- `cd frontend && npm install`：安装前端依赖。
- `cd frontend && npm run dev`：启动 Vite 开发服务器。
- `cd frontend && npm run build`：生成生产构建。
- `cd backend && uvicorn app.main:app --reload`：启动 FastAPI 后端。
- `cd backend && pytest`：运行后端测试。

提交前应至少运行与本次改动相关的构建、lint 或测试命令。

## 编码风格与命名约定

前端使用 Vue 3 单文件组件，组件名采用 PascalCase，如 `PromptEditor.vue`、`InterpretationResult.vue`。组合式函数使用 `useXxx.ts` 命名。后端 Python 代码遵循 PEP 8，模块与函数使用 snake_case。JSON 字段保持与 `blood_testcase.json` 一致，例如 `test_name`、`patient_id`、`reference_range`。

Prompt、医学规则和免责声明应集中管理，避免散落在多个组件中。涉及医学结论时必须保持审慎表达，并固定追加：“AI建议仅供参考，请以临床医生诊断为准。”

## 测试指南

测试应覆盖 JSON 格式校验、异常值识别、Prompt 读取与保存、API Key 未配置错误、AI 解读结果渲染、异常项红色高亮和 PDF 导出入口。前端建议使用 Vitest，后端建议使用 pytest。测试文件命名示例：`interpretation.spec.ts`、`test_interpret.py`。

## Commit 与 Pull Request 规范

当前目录未检测到 Git 历史；后续提交请使用小而清晰的提交，例如 `feat: scaffold vue fastapi app`、`test: cover blood report validation`。每个子任务完成后，必须先进行 CR（Code Review），CR 通过后再以一个小变更为单位 commit 并推送到 GitHub 仓库 `git@github.com:alickll909/onemate.git`。

PR 描述应包含改动摘要、验证命令、关联需求或任务编号；涉及 UI 的改动需附截图或录屏，涉及医学逻辑的改动需说明边界与安全限制。
