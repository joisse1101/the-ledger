import * as fs from 'node:fs'
import * as os from 'node:os'
import * as path from 'node:path'
import { describe, expect, it } from 'vitest'
import { clampToDisplays, DEFAULT_SIZE, loadState, saveState } from '../src/main/state'

const screen = { x: 0, y: 0, width: 1920, height: 1040 }
const second = { x: 1920, y: 0, width: 1280, height: 1024 }

describe('clampToDisplays', () => {
  it('keeps a visible position unchanged', () => {
    const saved = { x: 100, y: 120, width: 320, height: 260 }
    expect(clampToDisplays(saved, [screen])).toEqual(saved)
  })

  it('keeps a position on a second display', () => {
    const saved = { x: 2000, y: 50, width: 300, height: 240 }
    expect(clampToDisplays(saved, [screen, second])).toEqual(saved)
  })

  it('moves a window whose display was unplugged back onto the first display', () => {
    const result = clampToDisplays({ x: 2500, y: 50, width: 300, height: 240 }, [screen])
    expect(result.x).toBeGreaterThanOrEqual(0)
    expect(result.x + result.width).toBeLessThanOrEqual(screen.width)
  })

  it('moves a window that is almost entirely off screen', () => {
    const result = clampToDisplays({ x: -290, y: 10, width: 300, height: 240 }, [screen])
    expect(result.x).toBeGreaterThanOrEqual(0)
  })

  it('starts in the top-right corner on first run', () => {
    const result = clampToDisplays(null, [screen])
    expect(result).toMatchObject({ ...DEFAULT_SIZE, y: 16 })
    expect(result.x + result.width).toBeLessThan(screen.width)
  })

  it('shrinks a window larger than the display', () => {
    const result = clampToDisplays({ x: 0, y: 0, width: 5000, height: 5000 }, [screen])
    expect(result.width).toBe(screen.width)
    expect(result.height).toBe(screen.height)
  })
})

describe('persistence', () => {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'widget-')), 'nested', 'state.json')

  it('round-trips the bounds and collapsed flag', () => {
    const state = { bounds: { x: 10, y: 20, width: 300, height: 240 }, collapsed: true, opacity: 0.7 }
    saveState(file, state)
    expect(loadState(file)).toEqual(state)
  })

  it('falls back to defaults for a missing or corrupt file', () => {
    expect(loadState(path.join(os.tmpdir(), 'does-not-exist.json'))).toEqual({ bounds: null, collapsed: false, opacity: 1 })
    fs.writeFileSync(file, '{not json')
    expect(loadState(file)).toEqual({ bounds: null, collapsed: false, opacity: 1 })
    fs.writeFileSync(file, JSON.stringify({ bounds: { x: 'a' }, collapsed: 1 }))
    expect(loadState(file)).toEqual({ bounds: null, collapsed: false, opacity: 1 })
  })
})
