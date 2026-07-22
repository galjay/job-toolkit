<template>
  <section class="document-input">
    <div class="document-input__head">
      <div>
        <span class="step-label">{{ eyebrow }}</span>
        <h2>{{ title }}</h2>
      </div>
      <span class="char-count">{{ modelValue.length.toLocaleString() }} 字</span>
    </div>

    <textarea
      class="field-textarea document-textarea"
      :value="modelValue"
      :placeholder="placeholder"
      @input="$emit('update:modelValue', $event.target.value)"
    />

    <div class="document-actions">
      <input
        ref="fileInput"
        hidden
        type="file"
        accept=".pdf,.docx"
        @change="uploadFile"
      />
      <button class="secondary-button" type="button" :disabled="uploading" @click="fileInput.click()">
        <Upload :size="16" />
        {{ uploading ? '解析中' : '上传 PDF / DOCX' }}
      </button>
      <span v-if="filename" class="filename">{{ filename }}</span>
    </div>
    <p v-if="error" class="input-error">{{ error }}</p>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { Upload } from '@element-plus/icons-vue'

import api, { apiErrorMessage } from '../api/client'


defineProps({
  modelValue: { type: String, default: '' },
  eyebrow: { type: String, default: '' },
  title: { type: String, required: true },
  placeholder: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])
const fileInput = ref(null)
const uploading = ref(false)
const filename = ref('')
const error = ref('')

async function uploadFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  uploading.value = true
  error.value = ''
  try {
    const body = new FormData()
    body.append('file', file)
    const { data } = await api.post('/documents/parse', body)
    emit('update:modelValue', data.text)
    filename.value = file.name
  } catch (requestError) {
    error.value = apiErrorMessage(requestError, '文件解析失败')
  } finally {
    uploading.value = false
    event.target.value = ''
  }
}
</script>

<style scoped>
.document-input { min-width: 0; padding: 22px; }
.document-input__head { display: flex; justify-content: space-between; gap: 16px; margin-bottom: 14px; }
.step-label { color: var(--accent); font-size: 11px; font-weight: 800; text-transform: uppercase; }
h2 { margin: 4px 0 0; font-size: 17px; }
.char-count { flex: none; color: var(--muted); font-size: 12px; }
.document-textarea { min-height: 240px; }
.document-actions { display: flex; align-items: center; gap: 10px; margin-top: 12px; min-height: 40px; }
.secondary-button { display: inline-flex; align-items: center; gap: 7px; }
.filename { min-width: 0; overflow: hidden; color: var(--muted); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.input-error { margin: 8px 0 0; color: var(--danger); font-size: 12px; }
@media (max-width: 600px) { .document-input { padding: 16px; } .document-textarea { min-height: 190px; } }
</style>
