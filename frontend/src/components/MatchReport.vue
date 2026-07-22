<template>
  <section class="report-section">
    <div class="score-block">
      <div class="score-ring" :style="{ '--score': `${analysis.match_score * 3.6}deg` }">
        <span>{{ analysis.match_score }}</span>
        <small>匹配度</small>
      </div>
      <div>
        <span class="report-kicker">目标岗位</span>
        <h2>{{ analysis.target_role || '岗位匹配分析' }}</h2>
        <p>分数用于定位修改重点，不代表实际录用概率。</p>
      </div>
    </div>

    <div class="report-columns">
      <div>
        <h3>已经匹配</h3>
        <article v-for="item in analysis.strengths" :key="item.name" class="report-item strength">
          <strong>{{ item.name }}</strong>
          <p>{{ item.evidence }}</p>
          <small v-if="item.suggestion">{{ item.suggestion }}</small>
        </article>
        <p v-if="!analysis.strengths.length" class="empty-copy">暂未识别到明确匹配项</p>
      </div>
      <div>
        <h3>需要补强</h3>
        <article v-for="item in analysis.gaps" :key="item.name" class="report-item gap">
          <strong>{{ item.name }}</strong>
          <p>{{ item.evidence }}</p>
          <small>{{ item.suggestion }}</small>
        </article>
        <p v-if="!analysis.gaps.length" class="empty-copy">没有明显能力缺口</p>
      </div>
    </div>

    <div v-if="analysis.risks.length" class="risk-list">
      <h3>投递前核对</h3>
      <div v-for="risk in analysis.risks" :key="`${risk.section}-${risk.issue}`" class="risk-row">
        <strong>{{ risk.section }}</strong>
        <span>{{ risk.issue }}</span>
        <em>{{ risk.action }}</em>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({ analysis: { type: Object, required: true } })
</script>

<style scoped>
.report-section { padding: 24px; border-top: 1px solid var(--line); }
.score-block { display: flex; align-items: center; gap: 22px; padding-bottom: 22px; }
.score-ring { width: 108px; height: 108px; flex: none; display: grid; place-content: center; text-align: center; border-radius: 50%; background: radial-gradient(circle at center, white 59%, transparent 60%), conic-gradient(var(--accent) var(--score), #e6eaed 0); }
.score-ring span { font-size: 32px; font-weight: 800; line-height: 1; }
.score-ring small { margin-top: 5px; color: var(--muted); font-size: 11px; }
.report-kicker { color: var(--accent); font-size: 11px; font-weight: 800; }
.score-block h2 { margin: 5px 0; font-size: 21px; }
.score-block p { margin: 0; color: var(--muted); font-size: 12px; }
.report-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; }
h3 { margin: 0 0 12px; font-size: 14px; }
.report-item { padding: 11px 12px; margin-bottom: 8px; border-left: 3px solid; background: #f7f9fa; }
.report-item.strength { border-color: #2f8f68; }
.report-item.gap { border-color: #d09a34; }
.report-item strong { font-size: 13px; }
.report-item p { margin: 4px 0; color: #45515d; font-size: 12px; line-height: 1.5; }
.report-item small { color: var(--muted); }
.empty-copy { color: var(--muted); font-size: 12px; }
.risk-list { margin-top: 24px; padding-top: 18px; border-top: 1px solid var(--line); }
.risk-row { display: grid; grid-template-columns: 100px 1fr 1fr; gap: 12px; padding: 9px 0; font-size: 12px; border-bottom: 1px solid #edf0f2; }
.risk-row em { color: var(--blue); font-style: normal; }
@media (max-width: 700px) { .report-columns { grid-template-columns: 1fr; } .risk-row { grid-template-columns: 1fr; gap: 3px; } }
</style>
