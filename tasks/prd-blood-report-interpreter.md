# PRD: 血常规报告解读智能体 (OneMate)

## 1. Introduction / 概述

医智通(OneMate) 是一个 AI 医生助手。本模块为 **血常规报告解读智能体**，旨在帮助医生快速理解患者的血常规检验数据。医生粘贴血常规 JSON 数据后，AI 自动识别异常指标、用通俗语言解读、并输出结构化报告。系统支持自定义 System Prompt，提供独立的管理页面配置 DeepSeek API Key。

## 2. Goals / 目标

1. **5分钟内** 完成全栈原型搭建并跑通端到端流程。
2. AI 解读结果中异常指标以**红色高亮**展示，无遗漏。
3. 解读结果底部**固定附加**免责声明："AI建议仅供参考，请以临床医生诊断为准。"
4. 支持将 AI 解读结果**一键导出为 PDF**。
5. 支持管理员在独立的页面中**配置 DeepSeek API Key**（持久化到内存 DB）。
6. 支持用户**自定义编辑 System Prompt** 并存库。

## 3. User Stories / 用户故事

| ID | As a... | I want to... | So that... |
|----|---------|-------------|-----------|
| US-01 | 医生 | 粘贴血常规 JSON 数据并提交 | AI 自动解读异常指标 |
| US-02 | 医生 | 看到异常指标以红色高亮展示 | 快速定位需要关注的指标 |
| US-03 | 医生 | 将解读结果导出为 PDF | 存档或与患者沟通 |
| US-04 | 管理员 | 在独立页面配置 DeepSeek API Key | 系统能调用大模型 |
| US-05 | 管理员 | 编辑系统 Prompt | 调整 AI 解读风格和医学要求 |
| US-06 | 医生 | 看到免责声明 | 明确 AI 仅为辅助工具 |

## 4. Functional Requirements / 功能需求

### FR-01: 血常规数据输入与验证
- **描述**: 用户在前端粘贴 JSON 格式的血常规数据，系统需校验 JSON 合法性。
- **验收标准**:
  - 提供多行文本框供用户粘贴 JSON
  - 提交时校验 JSON 格式，格式错误时前端即时提示
  - 校验 JSON 结构须符合 `blood_testcase.json` 定义的 schema（`test_name`, `patient_id`, `sample_time`, `results` 字段，`results` 内每个指标须包含 `name`, `value`, `unit`, `reference_range`）
- **输入格式**: 见 `blood_testcase.json`

### FR-02: System Prompt 管理
- **描述**: 用户可查看并编辑系统 Prompt，Prompt 内容存储于内存数据库。
- **验收标准**:
  - 页面提供文本框展示当前 Prompt
  - 用户可修改并保存，保存后写入 DB
  - 默认 Prompt 须包含异常值判定逻辑（参考标准范围）和解读要求
  - 每次 AI 调用时，从 DB 读取最新 Prompt 拼接 JSON 数据发送

### FR-03: DeepSeek API Key 配置
- **描述**: 管理员可在独立的管理页面配置 DeepSeek API Key。
- **验收标准**:
  - 独立的 `/admin` 页面
  - 输入框支持填写 DeepSeek API Key
  - Key 保存至内存 DB（会话级持久）
  - 未配置 Key 时，调用 AI 应返回明确错误提示

### FR-04: AI 报告解读
- **描述**: 用户提交血常规数据后，系统调用 DeepSeek 模型生成解读结果。
- **验收标准**:
  - 请求体 = System Prompt（从 DB 读取）+ 用户 JSON 数据
  - AI 须识别异常指标（超出 `reference_range` 的值）
  - AI 对每个异常项用通俗语言解读临床意义（如"白细胞升高可能提示存在感染"）
  - AI 结果中异常项名称/数值**须标记**，前端通过正则/标记语言识别并渲染为红色
  - 禁止 AI 编造医学结论——Prompt 中须强调"无法确认时需明确说明"
  - 加载中展示 loading 状态，请求失败展示错误信息

### FR-05: 异常指标红色高亮
- **描述**: 前端渲染 AI 输出时，异常指标以红色字体突出显示。
- **验收标准**:
  - AI 输出中标记的异常项在前端渲染为 `<span style="color:red">`
  - 正常指标颜色不变
  - 至少覆盖：白细胞(WBC)、血红蛋白(HGB)、血小板(PLT) 三项

### FR-06: 免责声明
- **描述**: 在每次解读结果下方固定展示免责声明。
- **验收标准**:
  - 声明文案："AI建议仅供参考，请以临床医生诊断为准。"
  - 声明位于解读结果末尾，以灰色/小字展示
  - 不可被 AI 输出内容覆盖

### FR-07: PDF 导出
- **描述**: 用户可将解读结果一键导出为 PDF 文件。
- **验收标准**:
  - 导出内容包含：AI 解读正文 + 异常项高亮（保留红色样式）+ 免责声明
  - 点击"导出 PDF"按钮触发下载
  - 使用前端 PDF 库（如 html2pdf.js 或 jsPDF）实现

## 5. Non-Goals / 非目标

| 项 | 说明 |
|----|------|
| 用户认证/登录 | 原型阶段不做登录鉴权 |
| 多模型切换 | 固定使用 DeepSeek，不做模型选择器 |
| 历史记录 | 不实现解读历史列表（仅当前会话可见） |
| 批量解读 | 不支持一次提交多份报告 |
| 患者数据持久化 | 血常规数据不作长期存储 |
| 多语言 | 仅支持中文 |
| 移动端适配 | 优先桌面浏览器体验 |

## 6. Dependencies / 依赖

| 依赖 | 用途 | 版本 |
|------|------|------|
| Vue 3 | 前端框架 | latest |
| Vite | 前端构建工具 | latest |
| FastAPI | Python Web 后端框架 | latest |
| Uvicorn | ASGI 服务器 | latest |
| DeepSeek API | 大模型推理 | - |
| html2pdf.js / jsPDF | 前端 PDF 生成 | latest |
| SQLite / Python dict | 内存数据库 | - |

## 7. Timeline & Priority / 时间线与优先级

| 阶段 | 时间 | 内容 | 优先级 |
|------|------|------|--------|
| Phase 1 | T+0-30min | 全栈架构搭建（Vue + Vite + FastAPI scaffold，API 路由） | P0 |
| Phase 2 | T+30-70min | AI 解读核心逻辑（System Prompt 设计、DeepSeek 对接、异常检测） | P0 |
| Phase 3 | T+70-90min | 前端交互（JSON 输入、异常高亮渲染、加载/错误状态） | P0 |
| Phase 4 | T+90-105min | 功能增强（Admin 页面 API Key 配置、Prompt 编辑、PDF 导出） | P1 |
| Phase 5 | T+105-120min | 合规与收尾（免责声明、Code Review、推送仓库） | P0 |

## 8. Risk Assessment / 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| DeepSeek API 不可用/超时 | 中 | 高 | 前端展示超时友好提示，后端设 timeout |
| AI 输出格式不稳定（异常标记不一致） | 中 | 中 | System Prompt 中要求固定标记格式（如 `**指标名**`），前端兼容多种标记 |
| API Key 未配置 | 低 | 高 | 前端预检 Key 状态并提示 |
| JSON 格式复杂导致校验遗漏 | 低 | 中 | 后端做二次 schema 校验 |

## 9. Accessibility Requirements / 可访问性

- 红色高亮异常项时，需配合文字标注（如加粗或 [异常] 标签），确保色盲用户可辨识。

## 10. Design Considerations / 设计考虑

### 页面布局

```
+---------------------------------------------------+
|  OneMate - 血常规报告解读                           |
+---------------------------------------------------+
|                                                    |
|  [ System Prompt 编辑区 (可折叠) ]                  |
|                                                    |
|  [ 血常规 JSON 粘贴框 ]                            |
|  [ 提交按钮 ]                                      |
|                                                    |
|  --- 解读结果 ---                                  |
|  白细胞计数: 12.5 ↑ (红色)  ← 异常项红色高亮      |
|  → 可能提示存在感染...                             |
|  血红蛋白: 145 (正常)                              |
|  ...                                               |
|                                                    |
|  AI建议仅供参考，请以临床医生诊断为准。              |
|                                                    |
|  [ 导出 PDF ]                                      |
|                                                    |
+---------------------------------------------------+

+---------------------------------------------------+
|  /admin - 管理配置                                  |
+---------------------------------------------------+
|  DeepSeek API Key: [________________] [保存]       |
+---------------------------------------------------+
```

### 组件树

```
App.vue
├── PromptEditor.vue       (可折叠 Prompt 编辑)
├── JsonInput.vue          (JSON 文本框 + 校验 + 提交)
├── LoadingSpinner.vue     (加载状态)
├── InterpretationResult.vue (解读结果渲染 + 红色高亮)
├── Disclaimer.vue         (固定免责声明)
├── ExportButton.vue       (PDF 导出按钮)
└── AdminPage.vue          (/admin API Key 配置)
     └── ApiKeyConfig.vue
```

## 11. Technical Considerations / 技术考虑

### 架构

```
Browser (Vue 3 + Vite)  ──HTTP──>  FastAPI Backend  ──HTTP──>  DeepSeek API
                                        │
                                   [Memory DB]
                                   - system_prompt (singleton)
                                   - api_key (singleton)
```

### API 设计

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/prompt` | 获取当前 System Prompt |
| POST | `/api/prompt` | 保存 System Prompt |
| GET | `/api/key` | 获取 API Key 状态（是否已配置） |
| POST | `/api/key` | 保存 DeepSeek API Key |
| POST | `/api/interpret` | 提交血常规 JSON 数据，返回 AI 解读结果 |

### 后端关键逻辑

```python
# POST /api/interpret
1. 接收 JSON body
2. 校验 JSON schema
3. 从 DB 读取 system_prompt
4. 从 DB 读取 api_key
5. 拼接 prompt = system_prompt + "\n" + json_data
6. 调用 DeepSeek API (带 timeout)
7. 返回 AI 响应文本
```

### System Prompt 设计要点

- 定义异常判定逻辑：超出 `reference_range` 为异常
- 要求 AI 以 `**指标名**` 格式标记异常项（前端据此渲染红色）
- 要求对每个异常项给出通俗解读
- 要求不确定时明确说明，禁止编造
- 示例注入：few-shot 示例帮助稳定输出格式

### PDF 导出方式

使用前端方案（html2pdf.js），直接捕获 DOM 元素（解读结果区域），保留红色高亮样式，生成并下载 PDF。

## 12. Success Metrics / 成功指标

1. **端到端可用**: 粘贴 JSON → 提交 → AI 返回解读 → 异常红显 → 导出 PDF，全链路 100% 可跑通。
2. **异常检出率**: AI 对 WBC/HGB/PLT 等关键指标异常识别准确率 ≥ 95%（基于已知异常 case）。
3. **响应时间**: 从提交到展示结果 ≤ 15 秒（依赖 DeepSeek API 响应速度）。
4. **无假阳性医学结论**: AI 不对不确定项给出确定性诊断。

## 13. Open Questions / 开放问题

1. DeepSeek API 的 endpoint URL 是否需要可配置？还是固定使用官方标准地址？
2. 是否需要支持 API Key 的明文/加密存储？原型阶段是否先明文存储？
3. PDF 导出是否需要包含"导出时间"水印？
4. 是否需要支持多份 JSON 交替解读（不存历史，但允许用户重新粘贴新数据覆盖当前）？
