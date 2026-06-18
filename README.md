# OneMate 血常规报告解读智能体

医智通(OneMate) AI 医生助手的核心模块——血常规报告解读智能体。面向临床医生，粘贴血常规 JSON 数据后，AI 自动识别异常指标并用通俗语言解读，支持异常项红色高亮展示和 PDF 导出。

## 主要功能

- **血常规数据输入**：粘贴 JSON 格式的血常规检验数据，支持格式校验
- **AI 智能解读**：对接 DeepSeek 大模型，自动识别超出参考范围的异常指标，提供临床意义解读
- **异常项高亮**：异常指标以红色醒目展示，异常项摘要区集中列出
- **System Prompt 自定义**：用户可编辑系统 Prompt，调整 AI 解读风格，Prompt 持久化到服务端内存 DB
- **DeepSeek API Key 管理**：独立管理页面配置 DeepSeek API Key，配置后持久化到会话级内存 DB
- **PDF 导出**：一键导出解读结果为 PDF 文件（保留异常项红色高亮样式）
- **免责声明**：解读结果底部固定展示"AI建议仅供参考，请以临床医生诊断为准。"

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | HTML + CSS + Vanilla JavaScript (Vite 构建) |
| 后端 | Python FastAPI + Uvicorn |
| 数据库 | 内存字典（内存数据库，会话级存储） |
| AI 模型 | DeepSeek Chat API |
| 构建工具 | Vite |

## 快速开始

### 前置要求

- Python 3.12+
- Node.js 18+
- DeepSeek API Key（[官网申请](https://platform.deepseek.com/)）

### 1. 克隆项目

```bash
git clone git@github.com:alickll909/onemate.git
cd onemate
```

### 2. 后端启动

```bash
# 创建虚拟环境（如已存在可跳过）
python3 -m venv .venv
source .venv/bin/activate  # macOS / Linux

# 安装依赖
pip install -r requirements.txt

# 启动后端服务（热重载）
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

后端默认监听 `http://127.0.0.1:8000`，自动生成 API 文档可访问 `http://127.0.0.1:8000/docs`。

### 3. 前端启动

新开一个终端窗口：

```bash
# 安装前端依赖
npm install

# 启动开发服务器
npm run dev
```

前端默认监听 `http://127.0.0.1:5173`，已配置代理转发 `/api` 请求到后端 8000 端口。

### 4. 使用

1. 打开浏览器访问 `http://127.0.0.1:5173`
2. 点击右上角导航栏 **管理配置**，填入 DeepSeek API Key 并保存
3. 返回 **解读** 页面，页面已预填血常规 JSON 示例数据
4. 可编辑 System Prompt 调整解读风格（可选）
5. 点击 **提交解读** 等待 AI 生成结果
6. 解读结果中异常项以红色高亮，底部有免责声明
7. 点击 **导出 PDF** 下载解读报告

### 示例 JSON 格式

```json
{
  "test_name": "Complete Blood Count",
  "patient_id": "P0001",
  "sample_time": "2026-06-18T09:30:00+08:00",
  "results": {
    "wbc": {
      "name": "白细胞计数",
      "value": 6.2,
      "unit": "10^9/L",
      "reference_range": "3.5-9.5"
    },
    "hgb": {
      "name": "血红蛋白",
      "value": 145,
      "unit": "g/L",
      "reference_range": "130-175"
    }
  }
}
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/prompt` | 获取当前 System Prompt |
| POST | `/api/prompt` | 保存 System Prompt |
| GET | `/api/key` | 查询 API Key 是否已配置 |
| POST | `/api/key` | 保存 DeepSeek API Key |
| POST | `/api/interpret` | 提交血常规 JSON，返回 AI 解读结果 |

## 项目结构

```
onemate/
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 应用入口、路由定义
│   ├── config.py                # 常量配置（DeepSeek URL、默认 Prompt 等）
│   ├── deepseek.py              # DeepSeek API 调用封装
│   ├── schemas.py               # Pydantic 请求/响应模型
│   ├── store.py                 # 内存数据库（session 级）
│   ├── report_validation.py     # JSON 校验、异常检测逻辑
│   └── tests/
│       └── test_interpret.py    # 后端测试
├── index.html                   # 前端页面（含完整 CSS + JS）
├── vite.config.js               # Vite 配置（含 API 代理）
├── package.json                 # 前端依赖
├── requirements.txt             # Python 依赖
├── blood_testcase.json          # 血常规 JSON 示例数据
├── tasks/
│   └── prd-blood-report-interpreter.md  # 产品需求文档
└── README.md
```

## 测试

```bash
source .venv/bin/activate
pytest backend/tests/ -v
```

## License

MIT
