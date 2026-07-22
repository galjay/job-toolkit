import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ResumePreview from './ResumePreview.vue'


const resume = {
  contact: { name: '张三', phone: '13800000000', email: 'test@example.com', city: '天津', target_role: '产品实习生', links: [] },
  summary: '关注用户研究。',
  education: [],
  experience: [],
  projects: [{ id: 'p1', name: '校园项目', role: '负责人', start_date: '', end_date: '', bullets: ['完成需求分析'] }],
  campus: [],
  skills: ['用户研究'],
  certifications: [],
}


describe('resume preview', () => {
  it('renders a readable resume instead of raw JSON', () => {
    const wrapper = mount(ResumePreview, { props: { resume, template: 'ats' } })
    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('校园项目')
    expect(wrapper.text()).not.toContain('"contact"')
    expect(wrapper.find('.template-ats').exists()).toBe(true)
  })

  it('switches layout without losing content', async () => {
    const wrapper = mount(ResumePreview, { props: { resume, template: 'ats' } })
    await wrapper.setProps({ template: 'campus' })
    expect(wrapper.find('.template-campus').exists()).toBe(true)
    expect(wrapper.text()).toContain('张三')
  })
})
