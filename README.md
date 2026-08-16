# 求职工坊

一个本地优先的简历与 JD 工作台。它参考了开源求职工具的产品方向，但采用独立的视觉、交互和代码结构重新实现。

## 功能

- 简历与 JD 文本输入、字数统计、草稿自动保存
- 简历匹配优化与只分析 JD 两种工作模式
- 匹配评分、证据链、优势、能力缺口、投递风险与行动建议
- 可审核的改写建议：接受、拒绝、编辑，强调人工核实
- 审核后的最终 ATS 投递版：单栏预览、纯文本导出、Word `.doc` 导出和浏览器打印为 PDF
- 本地证件照/职业照工作区：裁剪、比例、背景色、压缩和提示词资源
- 首次打开配置向导：直接输入文本 AI 和图片 AI 配置，测试后立即生效
- 无 API Key 时也能使用演示模式，方便先体验界面

## 本地运行

需要 Node.js 20 或更高版本：

```powershell
npm start
```

然后访问 http://127.0.0.1:5173。

首次打开时，按页面提示输入 API Key。配置通过本机后端保存到被 `.gitignore` 忽略的 `.runtime-config.json`，不会进入 GitHub。前端不会把 Key 写入源码或接口响应。

## 兼容接口

文本接口采用 OpenAI Chat Completions 兼容格式：

- `AI_API_KEY`
- `AI_BASE_URL`，例如 `https://api.deepseek.com/v1`
- `AI_MODEL`，例如 `deepseek-chat`

也可以在项目根目录创建 `.env` 作为启动默认值；推荐优先使用应用内设置向导。图片接口是可选项，没有图片 Key 时仍可以使用本地照片处理和提示词资源模式。

## 安全边界

- API Key 只由本机页面发送到本机后端，再由后端请求你自己填写的模型服务商。
- 项目不会自动把简历、JD 或 Key 上传到作者服务器。
- 不要把 `.env` 或 `.runtime-config.json` 提交到 GitHub。
- 截图、日志和 issue 中不要粘贴完整 API Key。

## 放到 GitHub

在 GitHub 创建一个空仓库后，在本目录执行：

```powershell
git init
git add .
git commit -m "feat: create Career Atelier workspace"
git branch -M main
git remote add origin https://github.com/<your-name>/<your-repo>.git
git push -u origin main
```

请先确认 `git status` 中没有 `.env` 或 `.runtime-config.json`。

## 开源致谢

项目功能方向参考了 `galjay/job-toolkit` 的公开产品思路。本项目没有把其仓库代码直接放入本项目；如果未来引入该仓库的具体代码片段，需要同时保留其 MIT License 文本和版权声明。

