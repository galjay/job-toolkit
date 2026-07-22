<template>
  <section class="resume-editor">
    <div class="editor-section">
      <h3>基本信息</h3>
      <div class="field-grid">
        <label><span>姓名</span><input v-model="resume.contact.name" class="field-input" /></label>
        <label><span>目标岗位</span><input v-model="resume.contact.target_role" class="field-input" /></label>
        <label><span>电话</span><input v-model="resume.contact.phone" class="field-input" /></label>
        <label><span>邮箱</span><input v-model="resume.contact.email" class="field-input" /></label>
        <label><span>城市</span><input v-model="resume.contact.city" class="field-input" /></label>
      </div>
    </div>

    <div class="editor-section">
      <h3>个人概述</h3>
      <textarea v-model="resume.summary" class="field-textarea" rows="4" />
    </div>

    <div class="editor-section">
      <div class="editor-heading"><h3>教育背景</h3><button type="button" @click="addEducation">添加</button></div>
      <article v-for="(item, index) in resume.education" :key="item.id || index" class="repeat-item">
        <div class="field-grid">
          <label><span>学校</span><input v-model="item.school" class="field-input" /></label>
          <label><span>专业</span><input v-model="item.major" class="field-input" /></label>
          <label><span>学历</span><input v-model="item.degree" class="field-input" /></label>
          <label><span>时间</span><input v-model="item.end_date" class="field-input" placeholder="2022.09 - 2026.06" /></label>
        </div>
        <button class="remove-button" type="button" title="删除教育经历" @click="resume.education.splice(index, 1)">删除</button>
      </article>
    </div>

    <div class="editor-section">
      <div class="editor-heading"><h3>实习/工作经历</h3><button type="button" @click="addExperience">添加</button></div>
      <article v-for="(item, index) in resume.experience" :key="item.id || index" class="repeat-item">
        <div class="field-grid">
          <label><span>单位</span><input v-model="item.organization" class="field-input" /></label>
          <label><span>职位</span><input v-model="item.role" class="field-input" /></label>
          <label><span>开始时间</span><input v-model="item.start_date" class="field-input" /></label>
          <label><span>结束时间</span><input v-model="item.end_date" class="field-input" /></label>
        </div>
        <label><span>工作内容，每行一条</span><textarea class="field-textarea" :value="item.bullets.join('\n')" @input="item.bullets = lines($event.target.value)" /></label>
        <button class="remove-button" type="button" title="删除工作经历" @click="resume.experience.splice(index, 1)">删除</button>
      </article>
    </div>

    <div class="editor-section">
      <div class="editor-heading"><h3>项目经历</h3><button type="button" @click="addProject">添加</button></div>
      <article v-for="(item, index) in resume.projects" :key="item.id || index" class="repeat-item">
        <div class="field-grid">
          <label><span>项目名称</span><input v-model="item.name" class="field-input" /></label>
          <label><span>角色</span><input v-model="item.role" class="field-input" /></label>
        </div>
        <label><span>项目内容，每行一条</span><textarea class="field-textarea" :value="item.bullets.join('\n')" @input="item.bullets = lines($event.target.value)" /></label>
        <button class="remove-button" type="button" title="删除项目经历" @click="resume.projects.splice(index, 1)">删除</button>
      </article>
    </div>

    <div class="editor-section">
      <h3>技能与证书</h3>
      <label><span>技能，用逗号分隔</span><textarea class="field-textarea" :value="resume.skills.join('，')" @input="resume.skills = tokens($event.target.value)" /></label>
      <label><span>证书与奖项，每行一条</span><textarea class="field-textarea" :value="resume.certifications.join('\n')" @input="resume.certifications = lines($event.target.value)" /></label>
    </div>
  </section>
</template>

<script setup>
import { toRef } from 'vue'

const props = defineProps({ modelValue: { type: Object, required: true } })
const resume = toRef(props, 'modelValue')

const lines = (value) => value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean)
const tokens = (value) => value.split(/[，,\n]/).map((item) => item.trim()).filter(Boolean)

function addEducation() {
  resume.value.education.push({ id: crypto.randomUUID(), school: '', degree: '', major: '', start_date: '', end_date: '', highlights: [] })
}
function addExperience() {
  resume.value.experience.push({ id: crypto.randomUUID(), organization: '', role: '', location: '', start_date: '', end_date: '', bullets: [] })
}
function addProject() {
  resume.value.projects.push({ id: crypto.randomUUID(), name: '', role: '', start_date: '', end_date: '', bullets: [] })
}
</script>

<style scoped>
.resume-editor { padding: 20px; }
.editor-section { padding: 16px 0; border-bottom: 1px solid #e7eaed; }
.editor-section:first-child { padding-top: 0; }
.editor-section:last-child { border-bottom: 0; }
h3 { margin: 0 0 12px; font-size: 14px; }
label { display: block; }
label > span { display: block; margin: 0 0 5px; color: var(--muted); font-size: 11px; font-weight: 700; }
.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.field-textarea { min-height: 74px; font-size: 12px; }
.editor-heading { display: flex; justify-content: space-between; align-items: center; }
.editor-heading button, .remove-button { background: none; border: 0; color: var(--blue); font-size: 12px; }
.repeat-item { position: relative; margin-top: 10px; padding: 12px; background: #f7f8f9; border-radius: 6px; }
.repeat-item label { margin-top: 8px; }
.remove-button { display: block; margin: 6px 0 0 auto; color: var(--danger); }
@media (max-width: 620px) { .field-grid { grid-template-columns: 1fr; } }
</style>
