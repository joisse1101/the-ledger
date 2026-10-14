import * as fs from 'node:fs'
import * as path from 'node:path'

export interface Rect {
  x: number
  y: number
  width: number
  height: number
}

/** Persisted between runs. `bounds` is always the expanded window; collapsing only changes height. */
export interface WidgetState {
  bounds: Rect | null
  collapsed: boolean
  /** Background opacity (text stays solid), MIN_OPACITY..1. */
  opacity: number
}

export const MIN_OPACITY = 0.1
export const DEFAULT_SIZE = { width: 300, height: 240 }
/** How much of the window must stay on a display for it to count as reachable. */
const MIN_VISIBLE = 48
const MARGIN = 16

const overlap = (a: Rect, b: Rect): { w: number; h: number } => ({
  w: Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x),
  h: Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y),
})

/**
 * Keeps a saved window position reachable: unchanged when enough of it is on some display,
 * otherwise moved to the top-right corner of the first display (also the default first run).
 */
export function clampToDisplays(saved: Rect | null, workAreas: Rect[]): Rect {
  const primary = workAreas[0] ?? { x: 0, y: 0, width: 1280, height: 720 }
  const size = {
    width: Math.min(saved?.width ?? DEFAULT_SIZE.width, primary.width),
    height: Math.min(saved?.height ?? DEFAULT_SIZE.height, primary.height),
  }
  if (saved) {
    const placed = { ...saved, ...size }
    const reachable = workAreas.some((area) => {
      const { w, h } = overlap(placed, area)
      return w >= MIN_VISIBLE && h >= MIN_VISIBLE
    })
    if (reachable) return placed
  }
  return {
    ...size,
    x: primary.x + primary.width - size.width - MARGIN,
    y: primary.y + MARGIN,
  }
}

export const clampOpacity = (value: unknown): number =>
  typeof value === 'number' && Number.isFinite(value) ? Math.min(1, Math.max(MIN_OPACITY, value)) : 1

export function loadState(file: string): WidgetState {
  try {
    const raw = JSON.parse(fs.readFileSync(file, 'utf8')) as Partial<WidgetState>
    const b = raw.bounds
    const valid =
      b && [b.x, b.y, b.width, b.height].every((n) => typeof n === 'number' && Number.isFinite(n))
    return { bounds: valid ? { x: b.x, y: b.y, width: b.width, height: b.height } : null, collapsed: raw.collapsed === true, opacity: clampOpacity(raw.opacity) }
  } catch {
    return { bounds: null, collapsed: false, opacity: 1 }
  }
}

export function saveState(file: string, state: WidgetState): void {
  try {
    fs.mkdirSync(path.dirname(file), { recursive: true })
    fs.writeFileSync(file, JSON.stringify(state), 'utf8')
  } catch {
    // A position that can't be saved is a minor loss, never a reason to crash the widget.
  }
}
