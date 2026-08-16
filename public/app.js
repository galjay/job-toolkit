const $ = (selector) => document.querySelector(selector)
const $$ = (selector) => [...document.querySelectorAll(selector)]

const state = {
  mode: 'match',
  config: { text_ai: false, image_ai: false, text_model: '' },
  result: null,
  loading: false,
  reviewStates: [],
  reviewReplacements: [],
  finalResume: '',
  ats: { name: '', role: '', contact: '' },
}

const DEMO_RESUME = `AI 产品项目 | 产品分析与运营\n负责产品功能规划、用户场景拆解和版本迭代，推动需求评审到上线复盘闭环。\n通过用户反馈和数据观察建立问题优先级，持续优化核心流程。\n\n项目经历 | 求职工具箱\n独立设计简历/JD 输入、匹配诊断和逐条改写流程，使用 AI 辅助开发并完成测试与迭代。`
const DEMO_JD = `岗位：AI 产品运营\n1. 负责 AI 产品的用户场景、功能规划和增长运营；\n2. 熟练掌握 SQL，具备独立数据分析、特征理解与实验评估能力；\n3. 了解 AIGC 基本原理及工作流，能推进跨团队协作；\n4. 逻辑清晰，能将复杂业务问题拆解为可执行方案。`

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char])
}

function showToast(message) {
  const toast = $('#toast')
  toast.textContent = message
  toast.classList.add('show')
  clearTimeout(showToast.timer)
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 3200)
}

async function api(path, options = {}) {
  let response
  try {
    response = await fetch(path, { headers: { 'content-type': 'application/json', ...(options.headers || {}) }, ...options })
  } catch (error) {
    const message = String(error?.message || '')
    if (/Failed to fetch|NetworkError|Load failed|ERR_CONNECTION_REFUSED/i.test(message)) {
      throw new Error('无法连接本机分析服务，请确认工作台仍在运行；如果刚刚打开页面，请刷新后再试')
    }
    throw new Error('网络请求失败，请检查本机服务和网络连接')
  }
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.message || '请求失败')
  return payload
}

function updateCounts() {
  $('#resumeCount').textContent = `${$('#resumeInput').value.length.toLocaleString()} 字`
  $('#jdCount').textContent = `${$('#jdInput').value.length.toLocaleString()} 字`
  localStorage.setItem('career-atelier-resume', $('#resumeInput').value)
  localStorage.setItem('career-atelier-jd', $('#jdInput').value)
  $('#sessionLabel').textContent = $('#jdInput').value.trim() ? ($('#jdInput').value.trim().split('\n')[0].slice(0, 24) || '目标岗位') : '未命名项目'
}

function formatAtsBodyHtml(text) {
  const sectionPattern = /^(个人简介|个人概述|个人总结|工作经历|项目经历|核心项目|教育经历|教育背景|校园经历|辅助经历|实习经历|技能|技术能力|专业技能|证书|自我评价|求职目标|工作经验|PROJECTS?|EXPERIENCE|EDUCATION|SKILLS?|SUMMARY|PROFESSIONAL SUMMARY|PROJECT EXPERIENCE|WORK EXPERIENCE)$/i
  const lines = String(text || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  const parts = []
  let list = []
  const flush = () => { if (list.length) { parts.push(`<ul>${list.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`); list = [] } }
  for (const line of lines) {
    const plain = line.replace(/^[•·●▪◦*\-]+\s*/, '').trim()
    if (/^[•·●▪◦*\-]\s*/.test(line)) { list.push(plain); continue }
    flush()
    if (sectionPattern.test(plain.replace(/[：:]$/, ''))) parts.push(`<h2>${escapeHtml(plain.replace(/[：:]$/, ''))}</h2>`)
    else if (plain.length <= 60 && /^[^。！？]{2,60}\s*[|｜]/.test(plain)) parts.push(`<h2>${escapeHtml(plain)}</h2>`)
    else parts.push(`<p>${escapeHtml(plain)}</p>`)
  }
  flush()
  return parts.join('') || '<div class="ats-empty">完成分析后，最终简历会在这里排版预览。</div>'
}

function atsMarkup() {
  const name = state.ats.name || '姓名待填写'
  const role = state.ats.role
  const contact = state.ats.contact
  return `<h1>${escapeHtml(name)}</h1>${role ? `<div class="ats-role">${escapeHtml(role)}</div>` : ''}${contact ? `<div class="ats-contact">${escapeHtml(contact)}</div>` : ''}${formatAtsBodyHtml(state.finalResume || $('#finalResumeInput').value)}`
}

function syncAtsFields() {
  state.ats.name = $('#atsName').value.trim()
  state.ats.role = $('#atsRole').value.trim()
  state.ats.contact = $('#atsContact').value.trim()
}

function updateAtsPreview() {
  const text = $('#finalResumeInput').value
  state.finalResume = text
  syncAtsFields()
  localStorage.setItem('career-atelier-final-resume', text)
  localStorage.setItem('career-atelier-final-format', 'v2')
  $('#atsPreview').innerHTML = atsMarkup()
  const hasResult = Boolean(state.result)
  const total = state.reviewStates.length
  const accepted = state.reviewStates.filter((item) => item === 'accepted').length
  const pending = state.reviewStates.filter((item) => item === 'pending').length
  const status = $('#deliveryStatus')
  const warning = $('#deliveryWarning')
  if (!hasResult) {
    status.textContent = '等待审核'; status.classList.remove('ready'); warning.textContent = '完成分析后，这里会生成最终投递版。'; warning.classList.remove('ready')
  } else if (pending) {
    status.textContent = `${accepted} / ${total} 已审核`; status.classList.remove('ready'); warning.textContent = `还有 ${pending} 条建议未审核，建议确认后再导出。`; warning.classList.remove('ready')
  } else {
    status.textContent = `${accepted} / ${total} 已审核`; status.classList.add('ready'); warning.textContent = '审核完成，可以导出 ATS 投递版。'; warning.classList.add('ready')
  }
}

function updateStatus(status = state.config) {
  state.config = status
  const ready = Boolean(status.text_ai)
  const chip = $('#statusChip')
  chip.classList.toggle('ready', ready)
  chip.querySelector('span').textContent = ready ? `已连接 · ${status.text_model || '文本 AI'}` : '演示模式'
  const settingsStatus = $('#settingsStatus')
  if (settingsStatus) {
    settingsStatus.textContent = `文本 AI：${ready ? '已连接' : '未配置'} · 图片 AI：${status.image_ai ? '已连接' : '提示词资源模式'}`
    settingsStatus.classList.toggle('ready', ready)
  }
}

async function refreshConfig() {
  try {
    updateStatus(await api('/api/config/status'))
    if (!state.config.text_ai && !sessionStorage.getItem('atelier-setup-skipped')) $('#onboardingModal').classList.remove('hidden')
  } catch {
    showToast('暂时无法读取本机后端，请确认服务已经启动')
  }
}

function setMode(mode) {
  state.mode = mode
  $$('.mode-button').forEach((button) => button.classList.toggle('active', button.dataset.mode === mode))
  $('#resumeInput').closest('.field-block').style.opacity = mode === 'jd' ? '.55' : '1'
  $('#resumeInput').closest('.field-block').style.pointerEvents = mode === 'jd' ? 'none' : 'auto'
}

function loadDemo() {
  $('#resumeInput').value = DEMO_RESUME
  $('#jdInput').value = DEMO_JD
  updateCounts()
  showToast('已载入一组演示材料，可以直接开始分析')
}

function renderList(items, className = 'list-item') {
  if (!items?.length) return `<div class="placeholder-row">暂无内容</div>`
  return items.map((item) => `<div class="${className}">${escapeHtml(item)}</div>`).join('')
}

function isAtsSectionHeading(value) {
  return /^(个人简介|个人概述|个人总结|工作经历|项目经历|核心项目|教育经历|教育背景|校园经历|辅助经历|实习经历|技能|技术能力|专业技能|证书|自我评价|求职目标|工作经验|PROJECTS?|EXPERIENCE|EDUCATION|SKILLS?|SUMMARY|PROFESSIONAL SUMMARY|PROJECT EXPERIENCE|WORK EXPERIENCE)$/i.test(String(value || '').replace(/[：:]$/, '').trim())
}

function isLikelyAtsName(value) {
  const text = String(value || '').trim()
  return text.length >= 2 && text.length <= 20 && !/(求职|岗位|目标|电话|手机|邮箱|教育|项目|技能)/.test(text) && /^[\u4e00-\u9fffA-Za-z·\s]+$/.test(text)
}

function inferAtsHeader(text) {
  const lines = String(text || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  const name = lines.slice(0, 3).find((line) => isLikelyAtsName(line)) || ''
  const roleLine = lines.find((line) => /^(求职方向|目标岗位|应聘职位)[:：]/.test(line)) || ''
  const contactLine = lines.find((line) => /1[3-9]\d{9}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/.test(line)) || ''
  const phone = contactLine.match(/1[3-9]\d{9}/)?.[0] || ''
  const email = contactLine.match(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/)?.[0] || ''
  return {
    name,
    role: roleLine.replace(/^(求职方向|目标岗位|应聘职位)[:：]?\s*/, '').trim(),
    contact: [phone, email].filter(Boolean).join(' · '),
  }
}

function normalizeResumeForAts(text) {
  const profile = inferAtsHeader(text)
  const knownName = state.ats.name.trim() || profile.name
  const lines = String(text || '').split(/\r?\n/)
  const cleaned = []
  let leading = true
  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (leading) {
      if (!line) continue
      const isHeaderLine = line === knownName || (cleaned.length < 3 && isLikelyAtsName(line)) || /^(求职方向|目标岗位|应聘职位)[:：]/.test(line) || /1[3-9]\d{9}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/.test(line)
      if (isHeaderLine) continue
      if (isAtsSectionHeading(line)) leading = false
    }
    cleaned.push(line)
  }
  return cleaned.join('\n').replace(/\n{3,}/g, '\n\n').trim()
}

function compactMatchText(value) {
  return String(value || '').toLowerCase().replace(/[^\u4e00-\u9fffA-Za-z0-9]+/g, '')
}

function rewriteMatchScore(original, line) {
  const source = compactMatchText(original)
  const target = compactMatchText(line)
  if (!source || !target) return 0
  if (target.includes(source)) return 1
  const chunkSize = 4
  const chunks = []
  for (let index = 0; index <= source.length - chunkSize; index += 1) chunks.push(source.slice(index, index + chunkSize))
  const hits = chunks.filter((chunk) => target.includes(chunk)).length
  const coverage = chunks.length ? hits / chunks.length : 0
  const prefix = source.slice(0, Math.min(6, source.length))
  return Math.max(coverage, target.includes(prefix) ? 0.6 : 0)
}

function findRewriteTarget(text, original) {
  const lines = String(text || '').split(/\r?\n/)
  let best = null
  lines.forEach((line, index) => {
    const trimmed = line.trim()
    if (!trimmed || isAtsSectionHeading(trimmed)) return
    const score = rewriteMatchScore(original, trimmed)
    if (!best || score > best.score) best = { index, line, score }
  })
  const sourceLength = compactMatchText(original).length
  const threshold = sourceLength >= 8 ? 0.18 : 0.35
  return best && best.score >= threshold ? best : null
}

function stripListPrefix(value) {
  return String(value || '').replace(/^\s*[•·●▪◦*\-]\s*/, '').trim()
}

function isRetryableAnalyzeError(error) {
  const message = String(error?.message || '')
  if (/Key 无效|没有权限|余额|额度|模型或接口地址|请先在设置/.test(message)) return false
  return /无法连接|网络|模型服务返回错误|有效 JSON|格式不规范|请求失败|超时|连接/.test(message)
}

function renderResult(result) {
  state.result = result
  const score = typeof result.score === 'number' ? result.score : null
  $('#emptyResult').classList.add('hidden')
  $('#resultContent').classList.remove('hidden')
  $('#resultTitle').textContent = result.mode === 'jd' ? '岗位信号已提炼' : '匹配简报已生成'
  $('#resultStamp').textContent = result.demo ? 'DEMO / REVIEWABLE' : 'AI / REVIEWABLE'
  $('#resultHeadline').textContent = result.headline || '分析完成，请开始审核。'
  $('#resultSummary').textContent = result.summary || ''
  $('#scoreNumber').textContent = score == null ? '—' : score
  $('#scoreRing').style.setProperty('--score', `${score == null ? 0 : score}%`)
  $('#strengthCount').textContent = result.strengths?.length || 0
  $('#gapCount').textContent = result.gaps?.length || 0
  $('#riskCount').textContent = result.risks?.length || 0
  $('#keywordCloud').innerHTML = (result.keywords || []).map((keyword) => `<span class="tag">${escapeHtml(keyword)}</span>`).join('') || '<span class="tag">等待提炼</span>'
  $('#actionList').innerHTML = (result.actions || []).map((action) => `<div class="action-item"><span class="priority">${escapeHtml(action.priority || 'P1')}</span><div><strong>${escapeHtml(action.title)}</strong><p>${escapeHtml(action.detail)}</p></div><span class="action-arrow">↗</span></div>`).join('')
  const rawResume = $('#resumeInput').value
  const profile = inferAtsHeader(rawResume)
  const inferredRole = $('#jdInput').value.trim().split(/\r?\n/)[0].replace(/^岗位[:：]\s*/, '').trim() || profile.role
  if (!$('#atsName').value.trim() && profile.name) {
    $('#atsName').value = profile.name
    state.ats.name = profile.name
    localStorage.setItem('career-atelier-name', profile.name)
  }
  if (!$('#atsContact').value.trim() && profile.contact) {
    $('#atsContact').value = profile.contact
    state.ats.contact = profile.contact
    localStorage.setItem('career-atelier-contact', profile.contact)
  }
  state.finalResume = normalizeResumeForAts(rawResume)
  $('#finalResumeInput').value = state.finalResume
  if (!$('#atsRole').value.trim() && inferredRole) $('#atsRole').value = inferredRole.slice(0, 60)
  state.reviewStates = (result.rewrite || []).map(() => 'pending')
  state.reviewReplacements = (result.rewrite || []).map(() => null)
  renderReview(result.rewrite || [])
}

function applyReviewDecision(index, decision) {
  const item = state.result?.rewrite?.[index]
  if (!item) return
  const previous = state.reviewStates[index]
  let next = $('#finalResumeInput').value || state.finalResume || $('#resumeInput').value
  if (decision === 'accepted' && previous !== 'accepted') {
    const suggestion = stripListPrefix(item.suggestion)
    if (!suggestion) return showToast('这条建议没有可写入的内容，请先手动编辑最终简历')
    if (item.original && next.includes(item.original)) {
      next = next.split(item.original).join(suggestion)
      state.reviewReplacements[index] = { mode: 'exact', before: item.original, after: suggestion }
    } else {
      const target = findRewriteTarget(next, item.original)
      if (!target) return showToast('没有定位到这条建议对应的原文，请先手动核对最终简历')
      const lines = next.split(/\r?\n/)
      const prefix = lines[target.index].match(/^(\s*[•·●▪◦*\-]\s*)/)?.[1] || ''
      const replacement = `${prefix}${suggestion}`
      lines[target.index] = replacement
      next = lines.join('\n')
      state.reviewReplacements[index] = { mode: 'line', before: target.line, after: replacement }
    }
  }
  if (decision === 'rejected' && previous === 'accepted') {
    const replacement = state.reviewReplacements[index]
    if (replacement?.mode === 'exact') next = next.split(replacement.after).join(replacement.before)
    if (replacement?.mode === 'line') {
      const lines = next.split(/\r?\n/)
      const lineIndex = lines.indexOf(replacement.after)
      if (lineIndex >= 0) {
        lines[lineIndex] = replacement.before
        next = lines.join('\n')
      } else next = next.replace(replacement.after, replacement.before)
    }
    state.reviewReplacements[index] = null
  }
  state.reviewStates[index] = decision
  $('#finalResumeInput').value = next
  renderReview(state.result.rewrite || [])
}

function renderReview(items) {
  if (!items.length) {
    $('#reviewList').innerHTML = '<div class="placeholder-row">这次分析没有返回改写建议，请换一份更完整的简历或 JD。</div>'
    $('#reviewCount').textContent = '0 / 0 已确认'
    updateAtsPreview()
    return
  }
  $('#reviewList').innerHTML = items.map((item, index) => `<article class="review-item" data-index="${index}"><p><strong>原文 / ORIGINAL</strong>${escapeHtml(item.original)}</p><p class="suggestion"><strong>建议 / SUGGESTION</strong>${escapeHtml(item.suggestion)}<br /><span style="color:var(--amber);font-size:9px">需人工核实</span></p><div class="review-actions"><button data-review="accept" class="${state.reviewStates[index] === 'accepted' ? 'selected' : ''}">接受</button><button data-review="reject" class="reject ${state.reviewStates[index] === 'rejected' ? 'selected' : ''}">拒绝</button></div></article>`).join('')
  const accepted = state.reviewStates.filter((value) => value === 'accepted').length
  $('#reviewCount').textContent = `${accepted} / ${items.length} 已确认`
  updateAtsPreview()
}

async function analyze(useDemo = false) {
  if (state.loading) return
  state.loading = true
  const button = $('#analyzeButton')
  button.disabled = true
  button.setAttribute('aria-busy', 'true')
  const startedAt = Date.now()
  let slowNoticeShown = false
  const updateProgress = () => {
    const seconds = Math.floor((Date.now() - startedAt) / 1000)
    button.querySelector('span:nth-child(2)').textContent = seconds >= 8 ? `模型分析中 · ${seconds}s` : '正在连接模型…'
    if (seconds >= 8 && !slowNoticeShown) {
      slowNoticeShown = true
      showToast('首次连接模型可能需要一点时间，请不要重复点击；页面正在等待当前结果')
    }
  }
  updateProgress()
  const progressTimer = setInterval(updateProgress, 1000)
  try {
    const request = { method: 'POST', body: JSON.stringify({ mode: state.mode, resume: $('#resumeInput').value, jd: $('#jdInput').value, demo: useDemo }) }
    let result
    for (let attempt = 0; attempt < 2; attempt += 1) {
      try {
        result = await api('/api/analyze', request)
        break
      } catch (error) {
        if (attempt === 0 && !useDemo && isRetryableAnalyzeError(error)) {
          button.querySelector('span:nth-child(2)').textContent = '首次请求未完成，正在重试…'
          await new Promise((resolve) => setTimeout(resolve, 800))
          continue
        }
        throw error
      }
    }
    renderResult(result)
    showToast(result.demo ? '演示简报已生成，所有建议都可继续审核' : '分析完成，请逐条确认建议')
  } catch (error) {
    showToast(error.message)
  } finally {
    clearInterval(progressTimer)
    state.loading = false
    button.disabled = false
    button.removeAttribute('aria-busy')
    button.querySelector('span:nth-child(2)').textContent = '开始分析'
  }
}

function valueOrEmpty(id) { return $(id).value.trim() }

async function saveConfig(prefix, onboarding = false, skipTest = false) {
  const text = { baseUrl: valueOrEmpty(`#${prefix}TextBase`), model: valueOrEmpty(`#${prefix}TextModel`) }
  const image = { baseUrl: valueOrEmpty(`#${prefix}ImageBase`), model: valueOrEmpty(`#${prefix}ImageModel`) }
  const textKey = valueOrEmpty(`#${prefix}TextKey`)
  const imageKey = valueOrEmpty(`#${prefix}ImageKey`)
  if (textKey) text.apiKey = textKey
  if (imageKey) image.apiKey = imageKey
  if (!text.baseUrl || !text.model) return showToast('请先填写文本 AI 的 Base URL 和模型名')
  const statusBox = onboarding ? null : $('#settingsStatus')
  if (onboarding && !text.apiKey && !state.config.text_ai) return showToast('请先填写文本 AI API Key，或选择演示模式')
  if (statusBox) statusBox.textContent = '正在测试连接…'
  try {
    if (!skipTest) await api('/api/config/test', { method: 'POST', body: JSON.stringify({ kind: 'text', text, image }) })
    const saved = await api('/api/config/save', { method: 'POST', body: JSON.stringify({ text, image }) })
    updateStatus(saved.status)
    if (onboarding) $('#onboardingModal').classList.add('hidden')
    else $('#settingsModal').classList.add('hidden')
    showToast(skipTest ? '配置已保存到本机，下一次分析时会验证' : '连接成功，配置已保存在本机')
  } catch (error) {
    if (statusBox) statusBox.textContent = error.message
    showToast(error.message)
  }
}

function openSettings() {
  $('#setTextBase').value = 'https://api.deepseek.com/v1'
  $('#setTextModel').value = state.config.text_model || 'deepseek-chat'
  $('#setImageBase').value = ''
  $('#setImageModel').value = ''
  $('#settingsModal').classList.remove('hidden')
  updateStatus()
}

async function clearConfig() {
  try {
    const cleared = await api('/api/config/clear', { method: 'POST', body: '{}' })
    updateStatus(cleared.status)
    $('#settingsModal').classList.add('hidden')
    sessionStorage.removeItem('atelier-setup-skipped')
    showToast('本机配置已清除')
  } catch (error) { showToast(error.message) }
}

function handleFile(input, targetId) {
  input.addEventListener('change', async () => {
    const file = input.files?.[0]
    if (!file) return
    if (/\.txt$|\.md$|text\//i.test(file.name + file.type)) {
      $(targetId).value = await file.text()
      updateCounts()
      showToast(`已导入 ${file.name}`)
    } else {
      showToast(`${file.name} 已选中；演示版请先粘贴解析后的文字内容`)
    }
  })
}

function exportDraft() {
  const result = state.result
  if (!result) return showToast('完成一次分析后再导出工作稿')
  const lines = ['# 求职工坊工作稿', '', `模式：${state.mode === 'jd' ? '只分析 JD' : '简历匹配优化'}`, '', '## 分析摘要', result.summary || '', '', '## 优势', ...(result.strengths || []).map((x) => `- ${x}`), '', '## 能力缺口', ...(result.gaps || []).map((x) => `- ${x}`), '', '## 投递风险', ...(result.risks || []).map((x) => `- ${x}`), '', '## 下一步动作', ...(result.actions || []).map((x) => `- [${x.priority}] ${x.title}：${x.detail}`), '', '## 简历原文', $('#resumeInput').value]
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = '求职工坊-工作稿.md'
  link.click()
  URL.revokeObjectURL(link.href)
  showToast('分析工作稿已下载；最终投递版请在下方最终交付区导出')
}

function downloadFile(filename, content, type) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

function getFinalResume() {
  const text = $('#finalResumeInput').value.trim()
  state.finalResume = text
  return text
}

function canExportAts() {
  syncAtsFields()
  if (!getFinalResume()) {
    showToast('请先完成分析，或在最终简历正文里填写内容')
    return false
  }
  const pending = state.reviewStates.filter((item) => item === 'pending').length
  if (state.result && pending) {
    showToast(`还有 ${pending} 条建议未审核，请先接受或拒绝`)
    return false
  }
  if (!state.ats.name.trim()) {
    showToast('请先在最终交付区填写姓名')
    $('#atsName').focus()
    return false
  }
  return true
}

function buildAtsText() {
  const header = [state.ats.name.trim(), state.ats.role.trim(), state.ats.contact.trim()].filter(Boolean)
  return [...header, '', getFinalResume()].join('\n')
}

function exportAtsText() {
  if (!canExportAts()) return
  downloadFile('Career_Atelier_ATS_简历.txt', buildAtsText(), 'text/plain;charset=utf-8')
  showToast('ATS 纯文本简历已下载')
}

function exportAtsWord() {
  if (!canExportAts()) return
  const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>${escapeHtml(state.ats.name)} - ATS 简历</title><style>@page{size:A4;margin:18mm 17mm}body{font-family:Arial,"Microsoft YaHei",sans-serif;color:#1e2625;line-height:1.6;font-size:10.5pt}h1{margin:0 0 2pt;font-size:23pt;line-height:1.2}h2{margin:15pt 0 5pt;padding-bottom:3pt;border-bottom:1px solid #c9d4cf;color:#1d3930;font-size:11pt}p{margin:0 0 5pt}ul{margin:4pt 0 8pt;padding-left:18pt}.ats-role{font-weight:bold;color:#49635c}.ats-contact{margin:3pt 0 12pt;padding-bottom:9pt;border-bottom:1px solid #c9d4cf;color:#53635e}</style></head><body>${atsMarkup()}</body></html>`
  downloadFile('Career_Atelier_ATS_简历.doc', html, 'application/msword;charset=utf-8')
  showToast('Word ATS 简历已下载，可直接用 Word 打开')
}

function printAts() {
  if (!canExportAts()) return
  updateAtsPreview()
  window.print()
}

function setupPhotoLab() {
  $('#photoFile').addEventListener('change', () => {
    const file = $('#photoFile').files?.[0]
    if (!file) return
    const url = URL.createObjectURL(file)
    $('#photoPreview').src = url
    $('#photoStage').classList.add('has-photo')
    showToast('照片已在本机预览，不会自动上传')
  })
  $('#bgColor').addEventListener('input', (event) => { $('#photoStage').style.background = event.target.value })
  $('#photoRatio').addEventListener('change', (event) => { $('#photoStage').style.aspectRatio = event.target.value })
  $('#promptButton').addEventListener('click', () => {
    $('#promptResult').textContent = '干净自然的职业头像，半身构图，柔和的侧前方光线，背景简洁，服装利落，眼神自然，保留真实面部特征，不改变年龄、身份和脸型，不添加夸张妆容；用于求职简历头像，商务但不僵硬。'
    $('#promptResult').classList.remove('hidden')
  })
}

function bindEvents() {
  $$('.mode-button').forEach((button) => button.addEventListener('click', () => setMode(button.dataset.mode)))
  $$('.nav-link').forEach((button) => button.addEventListener('click', () => document.getElementById(button.dataset.scroll).scrollIntoView({ behavior: 'smooth' })))
  $('#resumeInput').addEventListener('input', updateCounts); $('#jdInput').addEventListener('input', updateCounts)
  $$('[data-clear]').forEach((button) => button.addEventListener('click', () => { $(`#${button.dataset.clear}`).value = ''; updateCounts() }))
  handleFile($('#resumeFile'), '#resumeInput'); handleFile($('#jdFile'), '#jdInput')
  $('#analyzeButton').addEventListener('click', () => analyze(false)); $('#demoButton').addEventListener('click', () => { loadDemo(); analyze(true) }); $('#emptyDemoButton').addEventListener('click', () => { loadDemo(); analyze(true) })
  $('#openSettings').addEventListener('click', openSettings); $('#footerSettings').addEventListener('click', openSettings)
  $('#saveOnboarding').addEventListener('click', () => saveConfig('on', true)); $('#saveOnboardingDirect').addEventListener('click', () => saveConfig('on', true, true)); $('#saveSettings').addEventListener('click', () => saveConfig('set', false)); $('#saveSettingsDirect').addEventListener('click', () => saveConfig('set', false, true)); $('#clearConfig').addEventListener('click', clearConfig)
  $('#skipSetup').addEventListener('click', () => { sessionStorage.setItem('atelier-setup-skipped', '1'); $('#onboardingModal').classList.add('hidden'); showToast('已进入演示模式，随时可以在右上角设置 API Key') })
  $$('[data-close]').forEach((button) => button.addEventListener('click', () => $(`#${button.dataset.close}`).classList.add('hidden')))
  $('#reviewList').addEventListener('click', (event) => { const button = event.target.closest('[data-review]'); if (!button) return; const item = button.closest('.review-item'); const index = Number(item.dataset.index); applyReviewDecision(index, button.dataset.review === 'accept' ? 'accepted' : 'rejected') })
  $('#jumpDeliveryButton').addEventListener('click', () => { $('#delivery').scrollIntoView({ behavior: 'smooth' }); if (!state.result) showToast('先完成一次分析，最终简历区才会生成内容') })
  $('#finalResumeInput').addEventListener('input', updateAtsPreview);
  [['atsName', 'name'], ['atsRole', 'role'], ['atsContact', 'contact']].forEach(([id, key]) => {
    $(`#${id}`).addEventListener('input', (event) => { state.ats[key] = event.target.value; localStorage.setItem(`career-atelier-${key}`, event.target.value); updateAtsPreview() })
  })
  $('#exportButton').addEventListener('click', exportDraft)
  $('#exportTxtButton').addEventListener('click', exportAtsText)
  $('#exportWordButton').addEventListener('click', exportAtsWord)
  $('#printAtsButton').addEventListener('click', printAts)
  setupPhotoLab()
}

function hydrate() {
  $('#resumeInput').value = localStorage.getItem('career-atelier-resume') || ''
  $('#jdInput').value = localStorage.getItem('career-atelier-jd') || ''
  state.ats = { name: localStorage.getItem('career-atelier-name') || '', role: localStorage.getItem('career-atelier-role') || '', contact: localStorage.getItem('career-atelier-contact') || '' }
  const storedFinal = localStorage.getItem('career-atelier-final-resume') || ''
  const cleanSource = normalizeResumeForAts($('#resumeInput').value)
  state.finalResume = localStorage.getItem('career-atelier-final-format') === 'v2' || !cleanSource ? normalizeResumeForAts(storedFinal) : cleanSource
  localStorage.setItem('career-atelier-final-format', 'v2')
  $('#finalResumeInput').value = state.finalResume
  $('#atsName').value = state.ats.name
  $('#atsRole').value = state.ats.role
  $('#atsContact').value = state.ats.contact
  updateCounts(); bindEvents(); updateAtsPreview(); refreshConfig()
}

hydrate()

