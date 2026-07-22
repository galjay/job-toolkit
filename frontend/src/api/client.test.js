import { beforeEach, describe, expect, it } from 'vitest'

import api from './client'


describe('API client', () => {
  beforeEach(() => localStorage.clear())

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
