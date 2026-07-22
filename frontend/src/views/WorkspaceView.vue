<template>
  <div class="workspace-page">
    <header class="page-title no-print">
      <h1>简历与 JD 工作台</h1>
      <p>用同一条流程完成岗位拆解、匹配诊断、逐条改写和正式简历导出。</p>
    </header>

    <div class="mode-switch no-print" role="tablist">
      <button :class="{ active: mode === 'match' }" type="button" @click="mode = 'match'">简历匹配优化</button>
      <button :class="{ active: mode === 'jd' }" type="button" @click="mode = 'jd'">只分析 JD</button>
    </div>

    <div v-if="configLoaded && !textAiConfigured" class="config-banner no-print">
      AI 尚未配置。请在 <code>backend/.env</code> 中填写自己的 <code>AI_API_KEY</code>；文件解析、简历编辑和证件照仍可使用。
    </div>
    <div v-if="error" class="error-banner no-print">{{ error }}</div>

    <section class="input-grid no-print" :class="{ single: mode === 'jd' }">
      <DocumentInput
        v-if="mode === 'match'"
        v-model="resumeText"
        class="surface"
        eyebrow="第一步"
        title="现有简历"
        placeholder="粘贴简历全文，或上传可提取文字的 PDF / DOCX..."
      />
      <DocumentInput
        v-model="jdText"
        class="surface"
        :eyebrow="mode === 'match' ? '第二步' : '岗位输入'"
        title="目标岗位 JD"
        placeholder="粘贴岗位职责和任职要求，或上传 PDF / DOCX..."
      />
    </section>

    <div class="analyze-bar surface no-print">
      <div>
        <strong>{{ mode === 'match' ? '同时分析简历与岗位' : '提炼岗位核心要求' }}</strong>
        <span>{{ inputStatus }}</span>
      </div>
      <button class="primary-button" type="button" :disabled="!canAnalyze || loading" @click="analyze">
        <Search :size="17" />
        {{ loading ? 'AI 分析中' : '开始分析' }}
      </button>
    </div>

    <section v-if="mode === 'jd' && jdResult" class="surface jd-result no-print">
      <div class="result-heading"><span>岗位结论</span><h2>{{ jdResult.summary }}</h2></div>
      <div class="jd-columns">
        <div><h3>核心职责</h3><ul><li v-for="item in jdResult.responsibilities" :key="item">{{ item }}</li></ul></div>
        <div><h3>硬技能</h3><div class="tag-list"><span v-for="item in jdResult.hard_skills" :key="item">{{ item }}</span></div></div>
        <div><h3>软技能</h3><div class="tag-list muted"><span v-for="item in jdResult.soft_skills" :key="item">{{ item }}</span></div></div>
        <div><h3>学历与经验</h3><p>{{ jdResult.education || '未明确' }} · {{ jdResult.experience || '未明确' }}</p></div>
      </div>
      <div class="preparation"><h3>投递准备</h3><ol><li v-for="item in jdResult.preparation" :key="item">{{ item }}</li></ol></div>
    </section>

    <template v-if="mode === 'match' && analysis && resume">
      <section class="surface result-stack no-print">
        <MatchReport :analysis="analysis" />
        <SuggestionEditor
          :suggestions="analysis.suggestions"
          :decisions="decisions"
          @accept="acceptSuggestion"
          @reject="rejectSuggestion"
        />
      </section>

      <section class="resume-workspace">
        <aside class="surface editor-column no-print">
          <div class="editor-toolbar">
            <div><span>第四步</span><h2>确认最终内容</h2></div>
            <b v-if="unresolvedCount">{{ unresolvedCount }} 项待补充</b>
          </div>
          <ResumeEditor :model-value="resume" />
        </aside>

        <div class="preview-column">
          <div class="surface preview-toolbar no-print">
            <div><span>第五步</span><h2>选择模板并导出</h2></div>
            <TemplateSelector v-model="template" />
            <div v-if="template === 'campus'" class="photo-option">
              <label class="secondary-button">
                <PictureFilled :size="16" />加入照片
                <input hidden type="file" accept="image/png,image/jpeg" @change="loadResumePhoto" />
              </label>
              <button v-if="resumePhoto" class="text-button" type="button" @click="resumePhoto = ''">移除照片</button>
            </div>
            <div class="export-actions">
              <button class="secondary-button" type="button" @click="windowPrint"><Printer :size="16" />打印 / PDF</button>
              <button class="primary-button" type="button" :disabled="exporting" @click="downloadDocx"><Download :size="16" />{{ exporting ? '生成中' : '下载 Word' }}</button>
            </div>
          </div>
          <ResumePreview :resume="resume" :template="template" :photo="resumePhoto" />
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Download, PictureFilled, Printer, Search } from '@element-plus/icons-vue'

import api, { apiErrorMessage } from '../api/client'
import DocumentInput from '../components/DocumentInput.vue'
import MatchReport from '../components/MatchReport.vue'
import ResumeEditor from '../components/ResumeEditor.vue'
import ResumePreview from '../components/ResumePreview.vue'
import SuggestionEditor from '../components/SuggestionEditor.vue'
import TemplateSelector from '../components/TemplateSelector.vue'
import { useWorkflow } from '../composables/useWorkflow'


const mode = ref('match')
const resumeText = ref('')
const jdText = ref('')
const loading = ref(false)
const exporting = ref(false)
const error = ref('')
const textAiConfigured = ref(false)
const configLoaded = ref(false)
const jdResult = ref(null)
const template = ref('ats')
const resumePhoto = ref('')
const { analysis, resume, decisions, unresolvedCount, setAnalysis, acceptSuggestion, rejectSuggestion } = useWorkflow()

const canAnalyze = computed(() => {
  if (!textAiConfigured.value) return false
  if (mode.value === 'jd') return jdText.value.trim().length >= 10
  return resumeText.value.trim().length >= 10 && jdText.value.trim().length >= 10
})
const inputStatus = computed(() => {
  if (mode.value === 'jd') return jdText.value ? `已输入 ${jdText.value.length} 字` : '等待岗位描述'
  const ready = Number(resumeText.value.trim().length >= 10) + Number(jdText.value.trim().length >= 10)
  return `已准备 ${ready} / 2 份材料`
})

onMounted(async () => {
  try {
    const { data } = await api.get('/config/status')
    textAiConfigured.value = data.text_ai
  } catch {
    error.value = '无法连接后端，请确认 FastAPI 服务已经启动。'
  } finally {
    configLoaded.value = true
  }
})

async function analyze() {
  if (!canAnalyze.value || loading.value) return
  loading.value = true
  error.value = ''
  try {
    if (mode.value === 'jd') {
      const { data } = await api.post('/jd/analyze', { jd_text: jdText.value })
      jdResult.value = data
    } else {
      const { data } = await api.post('/workflow/analyze', {
        resume_text: resumeText.value,
        jd_text: jdText.value,
      })
      setAnalysis(data)
    }
  } catch (requestError) {
    error.value = apiErrorMessage(requestError, '分析失败，请检查模型配置')
  } finally {
    loading.value = false
  }
}

async function downloadDocx() {
  if (!resume.value || exporting.value) return
  exporting.value = true
  error.value = ''
  try {
    const { data } = await api.post('/resume/export/docx', {
      template: template.value,
      resume: resume.value,
      photo_data_url: template.value === 'campus' ? resumePhoto.value || null : null,
    }, { responseType: 'blob' })
    const url = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    link.download = `${resume.value.contact.name || 'resume'}_简历.docx`
    link.click()
    URL.revokeObjectURL(url)
  } catch (requestError) {
    error.value = apiErrorMessage(requestError, 'Word 文件生成失败')
  } finally {
    exporting.value = false
  }
}

function loadResumePhoto(event) {
  const file = event.target.files?.[0]
  if (!file || !/^image\/(png|jpeg)$/.test(file.type) || file.size > 2 * 1024 * 1024) {
    error.value = '照片仅支持 2 MB 以内的 JPG 或 PNG。'
    return
  }
  const reader = new FileReader()
  reader.onload = () => { resumePhoto.value = reader.result }
  reader.readAsDataURL(file)
}

const windowPrint = () => window.print()
</script>

<style scoped>
.workspace-page { display: flex; flex-direction: column; gap: 18px; }
.mode-switch { display: inline-flex; width: fit-content; padding: 3px; background: #e5e9ec; border-radius: 7px; }
.mode-switch button { min-height: 36px; padding: 0 14px; border: 0; border-radius: 5px; background: transparent; color: #52606c; font-weight: 700; }
.mode-switch button.active { background: white; color: var(--ink); box-shadow: 0 1px 3px rgba(20, 32, 44, .12); }
.input-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.input-grid.single { grid-template-columns: minmax(0, 760px); }
.analyze-bar { display: flex; justify-content: space-between; align-items: center; gap: 20px; padding: 16px 20px; }
.analyze-bar strong, .analyze-bar span { display: block; }
.analyze-bar strong { font-size: 14px; }
.analyze-bar span { margin-top: 3px; color: var(--muted); font-size: 11px; }
.analyze-bar .primary-button, .export-actions button, .photo-option label { display: inline-flex; align-items: center; justify-content: center; gap: 7px; }
.result-stack { overflow: hidden; }
.jd-result { padding: 24px; }
.result-heading span, .editor-toolbar span, .preview-toolbar > div:first-child span { color: var(--accent); font-size: 11px; font-weight: 800; }
.result-heading h2 { margin: 5px 0 20px; font-size: 18px; }
.jd-columns { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
.jd-columns h3, .preparation h3 { margin: 0 0 9px; font-size: 13px; }
.jd-columns p, .jd-columns li, .preparation li { font-size: 12px; line-height: 1.55; }
.tag-list { display: flex; flex-wrap: wrap; gap: 5px; }
.tag-list span { padding: 4px 7px; background: var(--accent-soft); color: var(--accent); font-size: 11px; border-radius: 4px; }
.tag-list.muted span { background: #edf0f2; color: #4f5c67; }
.preparation { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--line); }
.resume-workspace { display: grid; grid-template-columns: minmax(360px, .7fr) minmax(520px, 1.3fr); gap: 18px; align-items: start; }
.editor-column { position: sticky; top: 82px; max-height: calc(100vh - 100px); overflow: auto; }
.editor-toolbar, .preview-toolbar { padding: 18px 20px; }
.editor-toolbar { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--line); }
.editor-toolbar h2, .preview-toolbar h2 { margin: 3px 0 0; font-size: 17px; }
.editor-toolbar b { color: var(--warning); font-size: 11px; }
.preview-column { min-width: 0; }
.preview-toolbar { display: grid; gap: 14px; margin-bottom: 12px; }
.photo-option, .export-actions { display: flex; align-items: center; gap: 8px; }
.photo-option label { width: fit-content; }
.export-actions { justify-content: flex-end; border-top: 1px solid var(--line); padding-top: 13px; }
code { padding: 1px 4px; background: rgba(255,255,255,.65); border-radius: 3px; }
@media (max-width: 1000px) { .resume-workspace { grid-template-columns: 1fr; } .editor-column { position: static; max-height: none; } .jd-columns { grid-template-columns: 1fr 1fr; } }
@media (max-width: 700px) { .input-grid { grid-template-columns: 1fr; } .analyze-bar { align-items: stretch; flex-direction: column; } .jd-columns { grid-template-columns: 1fr; } .export-actions { align-items: stretch; flex-direction: column; } .export-actions button { width: 100%; } }
</style>
