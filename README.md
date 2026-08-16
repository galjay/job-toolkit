# 求职工具箱｜本地优先的简历与岗位匹配工作台

> 把简历优化、JD 分析、ATS 友好导出和求职照片准备放进一条本地工作流。

[查看仓库](https://github.com/galjay/job-toolkit)

## 5 分钟先看懂

| 你想知道的事 | 项目答案 |
| --- | --- |
| 解决什么问题？ | 求职者通常要在多个工具之间切换：读 JD、改简历、检查匹配度、整理格式、准备照片。 |
| 谁会使用？ | 需要针对具体岗位准备简历和职业形象材料的求职者，尤其是校招或初入职场用户。 |
| 核心产出是什么？ | JD 要求提炼、简历/JD 匹配分析、能力差距和投递风险、可审核的简历改写、ATS 友好 Word/PDF 输出。 |
| 产品取舍是什么？ | 本地优先、用户自带 API Key；AI 建议必须经过使用者审核，不把模型输出当成事实。 |

## Demo、截图与入口

当前仓库没有已验证的公开在线 Demo，建议先看截图，再本地运行：

- [简历与 JD 工作台截图](docs/screenshots/workbench.png)
- [本地证件照编辑器截图](docs/screenshots/local-photo-editor.png)
- [AI 职业形象照资源截图](docs/screenshots/career-portrait.png)
- [Windows 启动脚本](start.bat)
- [Docker 启动方式](docker-compose.yml)

## 核心工作流

**输入简历 + 输入 JD → 提炼岗位要求 → 对照简历 → 审核改写建议 → 导出投递材料**

### 简历与岗位匹配

- 上传 PDF/DOCX，或直接粘贴简历和岗位描述。
- 单独分析 JD，提炼职责、硬技能、软技能、关键词和准备建议。
- 联合分析简历与 JD，输出匹配度、优势证据、能力差距和投递风险。
- 逐条审核 AI 改写：采用、忽略或手动编辑。
- 使用三套简历模板：ATS 标准版、中文校招版、经验求职版。
- 导出可编辑 Word；浏览器打印可保存为文本型 PDF。

### 照片与职业形象材料

- 标准证件照在浏览器本地做人像分割、换底色、裁切、缩放和提亮。
- 支持一寸、二寸、小一寸、考试报名尺寸和六寸相纸排版。
- 提供 AI 职业形象照的身份保持、西装、背景和自然美化提示词资源。
- 配置兼容 OpenAI Image Edit 请求格式的图片接口后，才可直接生成职业形象照。

## AI / Codex 与产品本人的分工

**产品本人负责：**

- 明确求职场景、MVP 边界和“简历—JD—审核—导出”的主流程。
- 设计输出结构、审核节点、隐私边界和不编造经历/技能/数字的产品规则。
- 验收简历解析、匹配分析、改写审核、导出和照片处理等关键场景。
- 对最终投递材料负责，手动确认所有经历、数字和照片用途。

**AI / Codex 负责：**

- 将产品流程拆成前后端模块、接口、状态和可执行实现。
- 辅助完成文档解析、AI 编排、Vue 工作台、本地证件照画布和 Word 导出。
- 根据验收结果修复问题、补充测试和迭代项目文档。
- 在用户配置自己的模型接口后，生成结构化分析和改写建议；不替用户确认事实。

## 隐私与安全边界

- 项目不提供公共服务器、登录、注册、用户数据库或开发者后门页面。
- 简历、JD 和照片默认不写入项目目录；标准证件照处理在浏览器本地完成。
- AI 分析内容会发送到使用者自己配置的模型接口；项目不提供作者的 AI 额度。
- API Key 只通过环境变量提供给后端，不放进浏览器代码。
- 后端默认绑定 `127.0.0.1`，上传文件会检查扩展名、MIME、文件签名、大小和文档页数。
- 职业形象照适合简历和企业头像，不保证符合身份证、护照等法定证件要求。

## 当前限制

- AI 分析功能需要使用者自己的 API Key 和可用的 OpenAI Chat Completions 兼容接口。
- 不同模型的输出参数和图片接口格式可能不同，需要按服务商调整 `AI_OUTPUT_TOKEN_PARAM` 等配置。
- 直接生成职业形象照目前要求兼容 `/images/edits` 的 multipart 请求；不兼容时使用提示词资源模式。
- AI 匹配、改写和职业形象照都需要人工复核，不能保证模型判断或生成结果完全准确。
- 项目是本地工具，暂未提供账号体系、云端历史、多人协作和公开在线 Demo。

## 本地运行

环境要求：

- Python 3.11+
- Node.js 20+
- 使用者自己的 API Key
- Docker Desktop（可选）

### Windows 快速启动

```powershell
git clone https://github.com/galjay/job-toolkit.git
cd job-toolkit
Copy-Item .env.example .env
notepad .env
```

至少配置：

```dotenv
AI_API_KEY=使用者自己的 API Key
```

然后双击 `start.bat`，访问 <http://127.0.0.1:5173>。

### 手动启动

后端：

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

### Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

访问 <http://127.0.0.1:8080>。

## 模型配置示例

文本模型使用 OpenAI Chat Completions 兼容参数：

```dotenv
AI_API_KEY=your-ai-api-key
AI_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat
AI_MAX_OUTPUT_TOKENS=8192
AI_OUTPUT_TOKEN_PARAM=max_tokens
```

图片接口是可选的；没有图片 API 时，职业形象照提示词资源仍然可用：

```dotenv
IMAGE_API_KEY=
IMAGE_BASE_URL=
IMAGE_MODEL=
```

## 测试

```powershell
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
backend\.venv\Scripts\python.exe -m pytest backend\tests -q

cd frontend
npm test -- --run
npm run build
```

## 仓库结构

```text
backend/                 FastAPI、文档解析、AI 编排、Word 导出
frontend/                Vue 工作台、本地证件照画布
docs/screenshots/        工作台、证件照和职业形象照截图
docs/superpowers/specs/  已确认的产品与安全设计
docs/superpowers/plans/  实施与验收计划
```

## 下一步验证

下一轮应拿一份真实但已脱敏的简历和一个明确岗位 JD，完整走一遍“上传/粘贴 → 匹配分析 → 逐条审核 → Word 导出”，记录：

- JD 关键要求是否被完整提取；
- 匹配报告中的优势、差距和风险是否能在原简历中找到证据；
- AI 改写是否出现未经证实的经历、技能或数字；
- 导出的 Word 是否仍然可编辑、结构清晰、适合继续人工修改。

不要使用真实身份证件或未脱敏的敏感个人信息做公开演示。

## License

[MIT](LICENSE)
