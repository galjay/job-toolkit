<template>
  <article class="resume-sheet print-area" :class="`template-${template}`">
    <header class="resume-header">
      <div>
        <h1>{{ resume.contact.name || '姓名' }}</h1>
        <p v-if="resume.contact.target_role">{{ resume.contact.target_role }}</p>
      </div>
      <img v-if="template === 'campus' && photo" :src="photo" alt="简历照片" />
    </header>
    <p class="contact-line">{{ contactLine }}</p>

    <template v-for="section in sectionOrder" :key="section">
      <section v-if="section === 'summary' && resume.summary">
        <h2>个人概述</h2><p>{{ resume.summary }}</p>
      </section>
      <section v-else-if="section === 'skills' && resume.skills.length">
        <h2>核心技能</h2><p>{{ resume.skills.join(' · ') }}</p>
      </section>
      <section v-else-if="section === 'education' && resume.education.length">
        <h2>教育背景</h2>
        <div v-for="(item, index) in resume.education" :key="item.id || index" class="resume-entry">
          <h3>{{ [item.school, item.major, item.degree].filter(Boolean).join(' · ') }} <time>{{ dates(item) }}</time></h3>
          <ul><li v-for="point in item.highlights" :key="point">{{ point }}</li></ul>
        </div>
      </section>
      <section v-else-if="section === 'experience' && resume.experience.length">
        <h2>实习/工作经历</h2>
        <div v-for="(item, index) in resume.experience" :key="item.id || index" class="resume-entry">
          <h3>{{ [item.organization, item.role, item.location].filter(Boolean).join(' · ') }} <time>{{ dates(item) }}</time></h3>
          <ul><li v-for="point in item.bullets" :key="point">{{ point }}</li></ul>
        </div>
      </section>
      <section v-else-if="section === 'projects' && resume.projects.length">
        <h2>项目经历</h2>
        <div v-for="(item, index) in resume.projects" :key="item.id || index" class="resume-entry">
          <h3>{{ [item.name, item.role].filter(Boolean).join(' · ') }} <time>{{ dates(item) }}</time></h3>
          <ul><li v-for="point in item.bullets" :key="point">{{ point }}</li></ul>
        </div>
      </section>
      <section v-else-if="section === 'campus' && resume.campus.length">
        <h2>校园经历</h2><ul><li v-for="item in resume.campus" :key="item">{{ item }}</li></ul>
      </section>
      <section v-else-if="section === 'certifications' && resume.certifications.length">
        <h2>证书与奖项</h2><ul><li v-for="item in resume.certifications" :key="item">{{ item }}</li></ul>
      </section>
    </template>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  resume: { type: Object, required: true },
  template: { type: String, required: true },
  photo: { type: String, default: '' },
})

const orders = {
  ats: ['summary', 'skills', 'experience', 'projects', 'education', 'campus', 'certifications'],
  campus: ['education', 'experience', 'projects', 'campus', 'skills', 'certifications', 'summary'],
  experienced: ['summary', 'skills', 'experience', 'projects', 'education', 'certifications', 'campus'],
}
const sectionOrder = computed(() => orders[props.template] || orders.ats)
const contactLine = computed(() => [
  props.resume.contact.phone,
  props.resume.contact.email,
  props.resume.contact.city,
  ...(props.resume.contact.links || []),
].filter(Boolean).join('  |  '))

const dates = (item) => [item.start_date, item.end_date].filter(Boolean).join(' - ')
</script>

<style scoped>
.resume-sheet { width: 100%; min-height: 980px; padding: 48px 52px; background: white; border: 1px solid #d8dde1; color: #1b2229; box-shadow: 0 8px 28px rgba(26, 39, 52, .08); }
.resume-header { display: flex; justify-content: center; align-items: start; gap: 24px; text-align: center; }
.resume-header h1 { margin: 0; font-size: 28px; letter-spacing: 0; }
.resume-header p { margin: 5px 0 0; font-size: 13px; }
.resume-header img { width: 72px; height: 100px; object-fit: cover; border: 1px solid #d5d9dc; }
.contact-line { margin: 10px 0 18px; text-align: center; color: #4f5a64; font-size: 10px; }
section { margin-top: 15px; }
section h2 { margin: 0 0 7px; padding-bottom: 4px; border-bottom: 1.5px solid #1d2730; font-size: 14px; letter-spacing: 0; }
section > p, li { font-size: 11px; line-height: 1.55; }
section > p { margin: 0; }
.resume-entry { margin: 8px 0; }
.resume-entry h3 { display: flex; justify-content: space-between; gap: 16px; margin: 0; font-size: 11.5px; }
.resume-entry time { flex: none; color: #5d6670; font-size: 10px; font-weight: 400; }
ul { margin: 5px 0 0; padding-left: 18px; }
.template-campus section h2 { color: #1f5e88; border-color: #78a6c3; }
.template-campus .resume-header { justify-content: space-between; text-align: left; }
.template-experienced section h2 { border-bottom-width: 2px; color: #174b3f; }
@media (max-width: 700px) { .resume-sheet { min-height: 0; padding: 28px 24px; } .resume-entry h3 { display: block; } .resume-entry time { display: block; margin-top: 3px; } }
@media print { .resume-sheet { width: 210mm; min-height: 297mm; padding: 14mm 16mm; } }
</style>
