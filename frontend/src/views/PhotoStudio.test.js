import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import PhotoStudio from './PhotoStudio.vue'


describe('photo studio', () => {
  it('clearly separates legal-size local photos from generated career portraits', async () => {
    const wrapper = mount(PhotoStudio, {
      global: {
        stubs: {
          LocalPhotoEditor: { template: '<div>本地照片编辑器</div>' },
          CareerPortraitPanel: { template: '<div>职业形象照资源</div>' },
        },
      },
    })
    expect(wrapper.text()).toContain('标准证件照')
    expect(wrapper.text()).toContain('AI 职业形象照')
    await wrapper.findAll('.photo-mode button')[1].trigger('click')
    expect(wrapper.text()).toContain('法定证件')
    expect(wrapper.text()).toContain('职业形象照资源')
  })
})
