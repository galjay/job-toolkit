import { describe, expect, it } from 'vitest'

import { routes } from './index'


describe('product routes', () => {
  it('exposes only the workbench and photo studio', () => {
    expect(routes.map((route) => route.path)).toEqual(['/', '/photo'])
    expect(routes.map((route) => route.name)).toEqual(['Workspace', 'PhotoStudio'])
  })

  it('contains no authentication or developer route', () => {
    const paths = routes.map((route) => route.path).join(' ')
    expect(paths).not.toMatch(/login|register|dev/)
  })
})
