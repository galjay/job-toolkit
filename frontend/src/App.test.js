import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import App from './App.vue'


describe('application shell', () => {
  it('shows only the two real tools', () => {
    const wrapper = mount(App, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
          RouterView: { template: '<main />' },
        },
      },
    })

    expect(wrapper.text()).toContain('简历与 JD')
    expect(wrapper.text()).toContain('证件照')
    expect(wrapper.text()).not.toMatch(/登录|注册|开发者/)
  })
})
