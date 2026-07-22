<template>
  <div class="photo-page">
    <header class="page-title">
      <h1>证件照与职业形象照</h1>
      <p>标准尺寸照片在本地完成；需要生成西装和职业形象时，使用单独的提示词或图片模型。</p>
    </header>

    <div class="photo-mode" role="tablist">
      <button :class="{ active: mode === 'standard' }" type="button" @click="mode = 'standard'">
        <Crop :size="18" /><span><b>标准证件照</b><small>本地抠图、换底和排版</small></span>
      </button>
      <button :class="{ active: mode === 'career' }" type="button" @click="mode = 'career'">
        <MagicStick :size="18" /><span><b>AI 职业形象照</b><small>西装、白底和自然美化</small></span>
      </button>
    </div>

    <div v-if="mode === 'career'" class="use-boundary">
      AI 职业形象照适合简历、招聘网站和企业头像，不保证符合身份证、护照等法定证件要求。
    </div>

    <div class="surface photo-tool">
      <LocalPhotoEditor v-if="mode === 'standard'" />
      <CareerPortraitPanel v-else />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Crop, MagicStick } from '@element-plus/icons-vue'

import CareerPortraitPanel from '../components/photo/CareerPortraitPanel.vue'
import LocalPhotoEditor from '../components/photo/LocalPhotoEditor.vue'

const mode = ref('standard')
</script>

<style scoped>
.photo-page { max-width: 1040px; margin: 0 auto; }
.photo-mode { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
.photo-mode button { min-height: 66px; display: flex; align-items: center; gap: 12px; padding: 11px 16px; text-align: left; background: white; border: 1px solid var(--line); border-radius: 7px; color: #4f5b65; }
.photo-mode button.active { border-color: var(--accent); background: var(--accent-soft); color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
.photo-mode button > svg { width: 18px; height: 18px; flex: 0 0 18px; }
.photo-mode span, .photo-mode b, .photo-mode small { display: block; }
.photo-mode b { color: var(--ink); font-size: 13px; }
.photo-mode small { margin-top: 3px; color: var(--muted); font-size: 10px; }
.use-boundary { margin-bottom: 14px; padding: 11px 13px; background: #fff8e5; border: 1px solid #e8d397; border-radius: 6px; color: #704e00; font-size: 12px; }
.photo-tool { overflow: hidden; }
@media (max-width: 620px) { .photo-mode { grid-template-columns: 1fr; } }
</style>
