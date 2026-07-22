<template>
  <section class="suggestions">
    <div class="section-heading">
      <div>
        <span>逐条审核</span>
        <h2>改写建议</h2>
      </div>
      <small>AI 建议不会自动写入简历</small>
    </div>

    <article v-for="item in suggestions" :key="item.id" class="suggestion-row">
      <div class="suggestion-meta">
        <span>{{ item.section }}</span>
        <b v-if="item.requires_user_input">需要补充事实</b>
      </div>
      <div class="before-copy">{{ item.original }}</div>
      <textarea v-model="drafts[item.id]" class="field-textarea" rows="3" />
      <p class="reason">{{ item.reason }}<template v-if="item.keywords.length"> · {{ item.keywords.join(' / ') }}</template></p>
      <div class="decision-row">
        <span v-if="decisions[item.id]" :class="decisions[item.id]">{{ decisions[item.id] === 'accepted' ? '已采用' : '已忽略' }}</span>
        <button class="text-button" type="button" @click="$emit('reject', item)">忽略</button>
        <button class="primary-button" type="button" @click="$emit('accept', item, drafts[item.id])">采用改写</button>
      </div>
    </article>
    <p v-if="!suggestions.length" class="empty-state">当前没有需要逐条改写的内容。</p>
  </section>
</template>

<script setup>
import { reactive, watch } from 'vue'


const props = defineProps({
  suggestions: { type: Array, default: () => [] },
  decisions: { type: Object, default: () => ({}) },
})
defineEmits(['accept', 'reject'])
const drafts = reactive({})

watch(
  () => props.suggestions,
  (items) => items.forEach((item) => { drafts[item.id] = item.optimized }),
  { immediate: true },
)
</script>

<style scoped>
.suggestions { padding: 24px; border-top: 1px solid var(--line); }
.section-heading { display: flex; align-items: end; justify-content: space-between; gap: 20px; margin-bottom: 16px; }
.section-heading span { color: var(--accent); font-size: 11px; font-weight: 800; }
.section-heading h2 { margin: 3px 0 0; font-size: 18px; }
.section-heading small { color: var(--muted); }
.suggestion-row { display: grid; grid-template-columns: 130px minmax(160px, .8fr) minmax(260px, 1.2fr); gap: 12px; align-items: start; padding: 16px 0; border-top: 1px solid #e8ecef; }
.suggestion-meta span { display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; }
.suggestion-meta b { display: inline-block; margin-top: 8px; padding: 3px 6px; background: #fff3cd; color: #7a5500; font-size: 10px; border-radius: 4px; }
.before-copy { padding: 10px; background: #f5f6f7; color: #5b6670; font-size: 12px; line-height: 1.55; border-radius: 5px; text-decoration-color: #c44; }
.field-textarea { min-height: 82px; font-size: 12px; }
.reason { grid-column: 2 / 4; margin: 0; color: var(--muted); font-size: 11px; }
.decision-row { grid-column: 1 / 4; display: flex; justify-content: flex-end; align-items: center; gap: 8px; }
.decision-row span { margin-right: auto; font-size: 12px; font-weight: 700; }
.decision-row .accepted { color: var(--accent); }
.decision-row .rejected { color: var(--muted); }
@media (max-width: 760px) { .suggestion-row { grid-template-columns: 1fr; } .reason, .decision-row { grid-column: 1; } }
</style>
