import { createServer } from 'node:http'
import { readFile, writeFile, unlink } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.dirname(fileURLToPath(import.meta.url))
const PUBLIC_DIR = path.join(ROOT, 'public')
const RUNTIME_FILE = path.join(ROOT, '.runtime-config.json')
const PORT = Number(process.env.PORT || 5173)

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
}

function parseEnv(text) {
  return Object.fromEntries(
    text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith('#') && line.includes('='))
      .map((line) => {
        const index = line.indexOf('=')
        const key = line.slice(0, index).trim()
        const value = line.slice(index + 1).trim().replace(/^['"]|['"]$/g, '')
        return [key, value]
      }),
  )
}

async function readEnvFile(file) {
  try {
    return parseEnv(await readFile(file, 'utf8'))
  } catch {
    return {}
  }
}

const startupEnv = {
  ...(await readEnvFile(path.join(ROOT, '.env'))),
  ...process.env,
}

let runtime = {}
try {
  runtime = JSON.parse(await readFile(RUNTIME_FILE, 'utf8'))
} catch {
  runtime = {}
}

function getConfig() {
  return {
    text: {
      apiKey: runtime.text?.apiKey || startupEnv.AI_API_KEY || '',
      baseUrl: runtime.text?.baseUrl || startupEnv.AI_BASE_URL || 'https://api.deepseek.com/v1',
      model: runtime.text?.model || startupEnv.AI_MODEL || 'deepseek-chat',
    },
    image: {
      apiKey: runtime.image?.apiKey || startupEnv.IMAGE_API_KEY || '',
      baseUrl: runtime.image?.baseUrl || startupEnv.IMAGE_BASE_URL || '',
      model: runtime.image?.model || startupEnv.IMAGE_MODEL || '',
    },
  }
}

function hasRealKey(value) {
  const key = String(value || '').trim()
  return Boolean(key && !/^your-|^sk-your/i.test(key))
}

function statusPayload() {
  const config = getConfig()
  return {
    text_ai: hasRealKey(config.text.apiKey),
    image_ai: Boolean(hasRealKey(config.image.apiKey) && config.image.baseUrl && config.image.model),
    text_model: config.text.model,
    image_model: config.image.model,
  }
}

async function persistConfig(nextConfig) {
  runtime = {
    text: nextConfig.text,
    image: nextConfig.image,
    updatedAt: new Date().toISOString(),
  }
  await writeFile(RUNTIME_FILE, JSON.stringify(runtime, null, 2), 'utf8')
}

function safeBaseUrl(value) {
  const parsed = new URL(String(value || '').trim())
  if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('接口地址必须使用 http 或 https')
  return parsed.toString().replace(/\/$/, '')
}

function chatEndpoint(baseUrl) {
  const base = safeBaseUrl(baseUrl)
  return base.endsWith('/chat/completions') ? base : `${base}/chat/completions`
}

function providerError(status, raw) {
  const text = String(raw || '')
  if (status === 401 || status === 403) return 'Key 无效或没有权限，请检查服务商、Key 和接口地址是否匹配'
  if (status === 402 || /balance|quota|余额|额度/i.test(text)) return '账户余额或调用额度不足'
  if (status === 404) return '模型或接口地址不匹配，请检查 Base URL 和模型名'
  return `模型服务返回错误（${status}），请检查配置或稍后重试`
}

async function requestProvider(config, body) {
  if (!hasRealKey(config.apiKey)) throw new Error('请先在设置中配置文本 AI Key')
  let response
  try {
    response = await fetch(chatEndpoint(config.baseUrl), {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify({ ...body, model: config.model }),
      signal: AbortSignal.timeout(65000),
    })
  } catch {
    throw new Error('无法连接模型服务，请检查网络和 Base URL')
  }
  const raw = await response.text()
  if (!response.ok) throw new Error(providerError(response.status, raw))
  let payload
  try {
    payload = JSON.parse(raw)
  } catch {
    throw new Error('模型返回的内容不是有效 JSON')
  }
  return payload.choices?.[0]?.message?.content || ''
}

function extractJson(text) {
  const cleaned = String(text || '').replace(/^```json\s*/i, '').replace(/```$/i, '').trim()
  const first = cleaned.indexOf('{')
  const last = cleaned.lastIndexOf('}')
  try {
    return JSON.parse(first >= 0 && last > first ? cleaned.slice(first, last + 1) : cleaned)
  } catch {
    throw new Error('模型返回的分析格式不规范，系统会自动重试一次')
  }
}

function demoResult(mode) {
  const isJdOnly = mode === 'jd'
  return {
    mode,
    demo: true,
    score: isJdOnly ? null : 78,
    headline: isJdOnly ? '这是一个偏产品与数据协同的增长型岗位。' : '你的经历与岗位的主线匹配度不错，建议把数据结果写得更靠前。',
    summary: isJdOnly ? '岗位重视结构化分析、跨团队推进和 AI 工具理解。' : '已有产品规划、用户场景拆解和迭代经验，和岗位的能力主线相吻合。',
    strengths: ['能把复杂需求拆成可执行流程', '有产品规划与用户场景分析经验', '具备数据意识和持续迭代习惯'],
    gaps: ['补充可验证的业务结果和规模', '把 SQL / Python 或实验评估写得更具体', '增加与目标岗位关键词对应的项目证据'],
    risks: ['部分经历缺少量化结果，ATS 关键词命中可能偏低', '改写内容提交前需要逐条核实，不能自动补造数字'],
    actions: [
      { title: '把成果提前', detail: '将“负责/参与”改成“通过什么动作，带来什么结果”。', priority: 'P0' },
      { title: '补足证据', detail: '给每个核心能力绑定一个真实项目、工具或业务结果。', priority: 'P1' },
      { title: '统一关键词', detail: '在不堆砌的前提下，覆盖 JD 中的分析、实验与协作表达。', priority: 'P1' },
    ],
    rewrite: [
      { original: '负责产品功能规划和迭代', suggestion: '围绕用户场景拆解产品流程，推动核心功能从需求评审到上线复盘闭环。' },
      { original: '参与用户反馈分析', suggestion: '整理用户反馈并建立问题优先级，形成可追踪的迭代清单与验证节奏。' },
    ],
    keywords: ['产品规划', '数据分析', '用户研究', 'AIGC', '跨团队协作', '实验评估'],
  }
}

async function analyze(body) {
  const config = getConfig()
  if (!hasRealKey(config.text.apiKey) || body.demo) return demoResult(body.mode)
  const schema = '{"score": number|null, "headline": string, "summary": string, "strengths": string[], "gaps": string[], "risks": string[], "actions": [{"title": string, "detail": string, "priority": string}], "rewrite": [{"original": string, "suggestion": string}], "keywords": string[]}'
  const prompt = `你是严谨的求职顾问。请只返回合法 JSON，不要 Markdown，不要虚构用户没有提供的事实。所有建议必须标注需要人工核实。输出结构必须符合：${schema}。工作模式：${body.mode}。\n\n简历：\n${body.resume || '(未提供)'}\n\n岗位 JD：\n${body.jd || '(未提供)'}`
  const text = await requestProvider(config.text, {
    temperature: 0.2,
    max_tokens: 1800,
    messages: [
      { role: 'system', content: '你只输出 JSON。中文回答。' },
      { role: 'user', content: prompt },
    ],
  })
  return { ...extractJson(text), demo: false, mode: body.mode }
}

async function testProvider(body) {
  const saved = getConfig()
  const supplied = body.kind === 'image' ? body.image : body.text
  const config = { ...(body.kind === 'image' ? saved.image : saved.text), ...(supplied || {}) }
  if (!config?.apiKey || !config?.baseUrl) throw new Error('请完整填写 API Key 和 Base URL')
  const base = safeBaseUrl(config.baseUrl)
  let response
  try {
    response = await fetch(`${base}/models`, {
      headers: { authorization: `Bearer ${config.apiKey}` },
      signal: AbortSignal.timeout(15000),
    })
  } catch {
    throw new Error('本机后端无法连接该接口。请允许 Node.js 访问网络，或在可联网终端重新启动项目；这通常不是 API Key 本身的问题')
  }
  if (!response.ok) throw new Error(providerError(response.status, await response.text()))
  return { ok: true, message: '连接成功，可以保存配置' }
}

async function readBody(request) {
  let data = ''
  for await (const chunk of request) {
    data += chunk
    if (data.length > 5_000_000) throw new Error('请求内容过大')
  }
  return data ? JSON.parse(data) : {}
}

function json(response, status, payload) {
  response.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
    'access-control-allow-origin': 'http://127.0.0.1:5173',
  })
  response.end(JSON.stringify(payload))
}

async function handleApi(request, response, pathname) {
  try {
    if (request.method === 'GET' && pathname === '/api/config/status') return json(response, 200, statusPayload())
    if (request.method === 'POST' && pathname === '/api/config/test') return json(response, 200, await testProvider(await readBody(request)))
    if (request.method === 'POST' && pathname === '/api/config/save') {
      const body = await readBody(request)
      const current = getConfig()
      await persistConfig({
        text: { ...current.text, ...(body.text || {}) },
        image: { ...current.image, ...(body.image || {}) },
      })
      return json(response, 200, { ok: true, status: statusPayload() })
    }
    if (request.method === 'POST' && pathname === '/api/config/clear') {
      runtime = {}
      try { await unlink(RUNTIME_FILE) } catch {}
      return json(response, 200, { ok: true, status: statusPayload() })
    }
    if (request.method === 'POST' && pathname === '/api/analyze') return json(response, 200, await analyze(await readBody(request)))
    return json(response, 404, { error: 'not_found', message: '接口不存在' })
  } catch (error) {
    return json(response, 400, { error: 'request_failed', message: error.message || '请求失败' })
  }
}

const server = createServer(async (request, response) => {
  const requestUrl = new URL(request.url, `http://${request.headers.host || '127.0.0.1'}`)
  if (requestUrl.pathname.startsWith('/api/')) return handleApi(request, response, requestUrl.pathname)

  const requested = requestUrl.pathname === '/' ? '/index.html' : requestUrl.pathname
  const filePath = path.normalize(path.join(PUBLIC_DIR, requested))
  if (!filePath.startsWith(PUBLIC_DIR)) return response.writeHead(403).end('Forbidden')
  try {
    const file = await readFile(filePath)
    response.writeHead(200, { 'content-type': MIME_TYPES[path.extname(filePath)] || 'application/octet-stream' })
    response.end(file)
  } catch {
    response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' }).end('Not found')
  }
})

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Career Atelier running at http://127.0.0.1:${PORT}`)
})

