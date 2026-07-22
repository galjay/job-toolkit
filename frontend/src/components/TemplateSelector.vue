<template>
  <div class="template-selector" role="radiogroup" aria-label="简历模板">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      :class="{ active: modelValue === option.value }"
      @click="$emit('update:modelValue', option.value)"
    >
      <span>{{ option.name }}</span>
      <small>{{ option.description }}</small>
    </button>
  </div>
</template>

<script setup>
defineProps({ modelValue: { type: String, required: true } })
defineEmits(['update:modelValue'])

const options = [
  { value: 'ats', name: 'ATS 标准版', description: '单栏、无照片，机器读取优先' },
  { value: 'campus', name: '中文校招版', description: '教育与项目优先，可加入照片' },
  { value: 'experienced', name: '经验求职版', description: '概述与工作经历优先' },
]
</script>

<style scoped>
.template-selector { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
button { min-height: 66px; padding: 10px 12px; text-align: left; background: white; border: 1px solid #cdd4d9; border-radius: 6px; }
button:hover { border-color: var(--accent); }
button.active { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); background: var(--accent-soft); }
span, small { display: block; }
span { font-size: 13px; font-weight: 750; }
small { margin-top: 4px; color: var(--muted); font-size: 10px; line-height: 1.35; }
@media (max-width: 680px) { .template-selector { grid-template-columns: 1fr; } }
</style>
