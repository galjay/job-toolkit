import { beforeEach, describe, expect, it } from 'vitest'

import api, { apiErrorMessage } from './client'


describe('API client', () => {
  beforeEach(() => localStorage.clear())

  it('waits long enough for an AI response correction attempt', () => {
    expect(api.defaults.timeout).toBeGreaterThanOrEqual(130000)
  })

  it('turns an Axios timeout into a clear Chinese message', () => {
    const error = {
      code: 'ECONNABORTED',
      message: 'timeout of 70000ms exceeded',
    }

    expect(apiErrorMessage(error)).toBe('AI 处理超时，较长材料可能需要 1-2 分钟，请重试。')
  })

  it('never reads an old login token into request headers', async () => {
    localStorage.setItem('token', 'legacy-secret')
    let observed
    api.defaults.adapter = async (config) => {
      observed = config
      return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
    }

    await api.get('/health')

    expect(observed.headers.Authorization).toBeUndefined()
  })
})
