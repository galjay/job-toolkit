import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ResumeEditor from './ResumeEditor.vue'


const makeResume = (name) => ({
  contact: { name, phone: '', email: '', city: '', target_role: '', links: [] },
  summary: '',
  education: [],
  experience: [],
  projects: [],
  campus: [],
  skills: [],
  certifications: [],
})


describe('resume editor', () => {
  it('updates when a new analysis replaces the resume object', async () => {
    const wrapper = mount(ResumeEditor, { props: { modelValue: makeResume('第一份') } })
    expect(wrapper.find('input').element.value).toBe('第一份')
    await wrapper.setProps({ modelValue: makeResume('第二份') })
    expect(wrapper.find('input').element.value).toBe('第二份')
  })
})
