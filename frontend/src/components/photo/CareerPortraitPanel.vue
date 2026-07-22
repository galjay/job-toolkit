<template>
  <section class="career-panel">
    <div class="portrait-controls">
      <div class="control-grid">
        <label><span>职业气质</span><select v-model="options.presentation" class="field-input"><option value="neutral">自然中性</option><option value="masculine">稳重干练</option><option value="feminine">自然利落</option></select></label>
        <label><span>正式服装</span><select v-model="options.outfit" class="field-input"><option value="dark_suit">深色商务西装</option><option value="light_suit">浅灰商务西装</option><option value="shirt">纯色商务衬衫</option></select></label>
        <label><span>背景</span><select v-model="options.background" class="field-input"><option value="white">纯白</option><option value="light_gray">浅灰</option><option value="business_blue">商务蓝</option></select></label>
        <label><span>修饰程度</span><select v-model="options.retouch" class="field-input"><option value="none">仅校正光线</option><option value="light">轻度自然美化</option><option value="polished">适度精修</option></select></label>
      </div>
      <button class="primary-button" type="button" :disabled="loadingPrompt" @click="buildPrompt">{{ loadingPrompt ? '生成中' : '生成专属提示词' }}</button>
    </div>

    <div v-if="prompt" class="prompt-result">
      <div class="prompt-heading">
        <div><span>提示词资源</span><h2>可直接用于豆包等参考图工具</h2></div>
        <div class="prompt-actions"><button class="text-button" type="button" @click="copyPrompt">复制</button><button class="secondary-button" type="button" @click="downloadResource">下载资源</button></div>
      </div>
      <label><span>正向提示词</span><textarea v-model="prompt" class="field-textarea" rows="7" /></label>
      <label><span>负面约束</span><textarea v-model="negativePrompt" class="field-textarea muted-area" rows="5" /></label>
      <p class="usage-note">{{ usageNote }}</p>
    </div>

    <div class="generation-section">
      <div class="generation-copy">
        <span>可选：直接生成</span>
        <h2>{{ providerEnabled ? '图片接口已配置' : '未配置图片接口' }}</h2>
        <p v-if="providerEnabled">只有在你确认后，参考照片才会发送到你配置的第三方图片模型。</p>
        <p v-else>提示词资源始终可用。直接生成需要在本机配置兼容的图片 API，项目不会使用作者额度。</p>
      </div>

      <template v-if="providerEnabled">
        <div class="reference-row">
          <label class="secondary-button"><Upload :size="16" />选择正脸参考照<input hidden type="file" accept="image/jpeg,image/png" @change="loadReference" /></label>
          <img v-if="referencePreview" :src="referencePreview" alt="参考照片预览" />
          <span v-else>JPG / PNG，最大 8 MB</span>
        </div>
        <label class="consent-row"><input v-model="consent" type="checkbox" />我了解照片将发送给自己配置的第三方图片模型，并同意本次发送。</label>
        <button class="primary-button" type="button" :disabled="!referenceFile || !consent || generating" @click="generatePortrait">{{ generating ? '生成中，请勿关闭页面' : '生成职业形象照' }}</button>
      </template>

      <div v-if="generatedImage" class="generated-result">
        <img :src="generatedImage" alt="AI 生成的职业形象照" />
        <a class="primary-button" :href="generatedImage" download="AI职业形象照.png">下载图片</a>
      </div>
    </div>

    <p v-if="message" class="status-message">{{ message }}</p>
    <p v-if="error" class="error-banner">{{ error }}</p>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Upload } from '@element-plus/icons-vue'

import api, { apiErrorMessage } from '../../api/client'


const options = reactive({ presentation: 'neutral', outfit: 'dark_suit', background: 'white', retouch: 'light' })
const prompt = ref('')
const negativePrompt = ref('')
const usageNote = ref('')
const providerEnabled = ref(false)
const loadingPrompt = ref(false)
const referenceFile = ref(null)
const referencePreview = ref('')
const consent = ref(false)
const generating = ref(false)
const generatedImage = ref('')
const error = ref('')
const message = ref('')

onMounted(buildPrompt)

async function buildPrompt() {
  loadingPrompt.value = true
  error.value = ''
  try {
    const { data } = await api.post('/photo/prompt', options)
    prompt.value = data.prompt
    negativePrompt.value = data.negative_prompt
    usageNote.value = data.usage_note
    providerEnabled.value = data.provider_enabled
  } catch (requestError) {
    error.value = apiErrorMessage(requestError, '提示词生成失败')
  } finally {
    loadingPrompt.value = false
  }
}

async function copyPrompt() {
  const content = resourceText()
  try {
    await navigator.clipboard.writeText(content)
    message.value = '提示词已复制。'
  } catch {
    message.value = '浏览器不允许自动复制，请选中文本手动复制。'
  }
}

function downloadResource() {
  const blob = new Blob([resourceText()], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'AI职业形象照_提示词资源.txt'
  link.click()
  URL.revokeObjectURL(url)
}

function resourceText() {
  return `AI 职业形象照生成资源\n\n使用方式：上传本人的清晰正脸照片作为参考图，再粘贴以下内容。\n\n正向提示词：\n${prompt.value}\n\n负面约束：\n${negativePrompt.value}\n\n用途说明：\n${usageNote.value}\n`
}

function loadReference(event) {
  const file = event.target.files?.[0]
  if (!file || !/^image\/(jpeg|png)$/.test(file.type) || file.size > 8 * 1024 * 1024) {
    error.value = '请选择 8 MB 以内的 JPG 或 PNG。'
    return
  }
  referenceFile.value = file
  if (referencePreview.value) URL.revokeObjectURL(referencePreview.value)
  referencePreview.value = URL.createObjectURL(file)
  generatedImage.value = ''
  consent.value = false
}

async function generatePortrait() {
  if (!referenceFile.value || !consent.value || generating.value) return
  generating.value = true
  error.value = ''
  try {
    const body = new FormData()
    body.append('file', referenceFile.value)
    body.append('prompt', `${prompt.value}\n负面约束：${negativePrompt.value}`)
    body.append('consent', 'true')
    const { data } = await api.post('/photo/generate', body)
    generatedImage.value = data.image_data_url || data.image_url
  } catch (requestError) {
    error.value = `${apiErrorMessage(requestError, '图片生成失败')}。提示词资源仍可复制到其他工具使用。`
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.career-panel { display: grid; gap: 0; }
.portrait-controls, .prompt-result, .generation-section { padding: 24px; }
.prompt-result, .generation-section { border-top: 1px solid var(--line); }
.control-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 14px; }
label > span, .generation-copy > span, .prompt-heading span { display: block; margin-bottom: 6px; color: var(--muted); font-size: 11px; font-weight: 700; }
.prompt-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 14px; }
.prompt-heading h2, .generation-copy h2 { margin: 3px 0 0; font-size: 17px; }
.prompt-actions { display: flex; gap: 7px; }
.prompt-result label { display: block; margin-top: 11px; }
.prompt-result textarea { min-height: 100px; font-size: 12px; }
.muted-area { background: #f7f8f9; }
.usage-note, .generation-copy p { color: var(--muted); font-size: 12px; line-height: 1.55; }
.reference-row { display: flex; align-items: center; gap: 12px; margin: 18px 0 12px; }
.reference-row label { display: inline-flex; align-items: center; gap: 7px; }
.reference-row img { width: 58px; height: 72px; object-fit: cover; border: 1px solid var(--line); }
.reference-row span { color: var(--muted); font-size: 11px; }
.consent-row { display: flex; align-items: flex-start; gap: 8px; max-width: 720px; margin: 0 0 14px; color: #47535e; font-size: 12px; line-height: 1.45; }
.generated-result { display: flex; align-items: end; gap: 16px; margin-top: 20px; }
.generated-result img { width: min(300px, 100%); max-height: 430px; object-fit: contain; border: 1px solid var(--line); }
.generated-result a { display: inline-flex; align-items: center; justify-content: center; text-decoration: none; }
.status-message { margin: 0 24px 18px; color: var(--accent); font-size: 12px; }
.error-banner { margin: 0 24px 18px; }
@media (max-width: 850px) { .control-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 560px) { .control-grid { grid-template-columns: 1fr; } .prompt-heading { align-items: flex-start; flex-direction: column; } .generated-result { align-items: stretch; flex-direction: column; } }
</style>
