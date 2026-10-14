import * as path from 'node:path'
import { BrowserWindow, screen } from 'electron'
import { CHANNELS } from '../shared/ipc'
import type { LiveState } from '../shared/types'
import { clampToDisplays, saveState, type Rect, type WidgetState } from './state'

const PILL_HEIGHT = 34
const PILL_MAX_WIDTH = 240
const SAVE_DELAY_MS = 300

export interface WidgetWindow {
  window: BrowserWindow
  sendState(state: LiveState): void
  toggleCollapse(): void
  toggleVisible(): void
  show(): void
  isVisible(): boolean
}

/** The frameless always-on-top window, its remembered bounds and its collapse-to-pill toggle. */
export function createWidgetWindow(stateFile: string, saved: WidgetState): WidgetWindow {
  const workAreas = screen.getAllDisplays().map((d) => d.workArea)
  let bounds: Rect = clampToDisplays(saved.bounds, workAreas)
  let collapsed = saved.collapsed
  let lastState: LiveState | null = null
  let saveTimer: ReturnType<typeof setTimeout> | undefined

  const collapsedRect = (): Rect => ({
    x: bounds.x,
    y: bounds.y,
    width: Math.min(bounds.width, PILL_MAX_WIDTH),
    height: PILL_HEIGHT,
  })

  const window = new BrowserWindow({
    ...(collapsed ? collapsedRect() : bounds),
    frame: false,
    resizable: !collapsed,
    minWidth: 180,
    minHeight: PILL_HEIGHT,
    skipTaskbar: true,
    alwaysOnTop: true,
    fullscreenable: false,
    maximizable: false,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'index.js'),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
    },
  })
  // 'screen-saver' keeps it above ordinary always-on-top windows too.
  window.setAlwaysOnTop(true, 'screen-saver')
  window.setMenuBarVisibility(false)
  void window.loadFile(path.join(__dirname, '..', 'ui', 'renderer', 'index.html'))

  // The widget never navigates or opens windows; the renderer has no business leaving its page.
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  window.webContents.on('will-navigate', (event) => event.preventDefault())

  const push = () => {
    window.webContents.send(CHANNELS.collapsed, collapsed)
    if (lastState) window.webContents.send(CHANNELS.state, lastState)
  }
  window.webContents.on('did-finish-load', () => {
    push()
    window.show()
  })

  const persist = () => {
    clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      const current = window.getBounds()
      // While collapsed only the position is meaningful; the expanded size is kept as it was.
      bounds = collapsed ? { ...bounds, x: current.x, y: current.y } : current
      saveState(stateFile, { bounds, collapsed })
    }, SAVE_DELAY_MS)
  }
  window.on('moved', persist)
  window.on('resized', persist)

  return {
    window,
    sendState(state) {
      lastState = state
      if (!window.isDestroyed()) window.webContents.send(CHANNELS.state, state)
    },
    toggleCollapse() {
      const current = window.getBounds()
      if (!collapsed) bounds = current
      collapsed = !collapsed
      window.setResizable(!collapsed)
      window.setBounds(collapsed ? { ...collapsedRect(), x: current.x, y: current.y } : { ...bounds, x: current.x, y: current.y })
      bounds = { ...bounds, x: current.x, y: current.y }
      saveState(stateFile, { bounds, collapsed })
      window.webContents.send(CHANNELS.collapsed, collapsed)
    },
    toggleVisible() {
      if (window.isVisible()) window.hide()
      else window.show()
    },
    show() {
      if (window.isMinimized()) window.restore()
      window.show()
      window.focus()
    },
    isVisible: () => window.isVisible(),
  }
}
