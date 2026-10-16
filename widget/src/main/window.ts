import * as path from 'node:path'
import { BrowserWindow, screen } from 'electron'
import { CHANNELS } from '../shared/ipc'
import type { LiveState, RemoteStatus } from '../shared/types'
import { clampOpacity, clampToDisplays, saveState, type Rect, type WidgetState } from './state'

const PILL_HEIGHT = 34
const PILL_MAX_WIDTH = 240
const SAVE_DELAY_MS = 300

export interface WidgetWindow {
  window: BrowserWindow
  sendState(state: LiveState): void
  sendRemote(status: RemoteStatus): void
  toggleCollapse(): void
  toggleVisible(): void
  setOpacity(value: number): void
  setContentHeight(height: number): void
  show(): void
  isVisible(): boolean
}

/** The frameless always-on-top window, its remembered bounds and its collapse-to-pill toggle. */
export function createWidgetWindow(stateFile: string, saved: WidgetState): WidgetWindow {
  const workAreas = screen.getAllDisplays().map((d) => d.workArea)
  let bounds: Rect = clampToDisplays(saved.bounds, workAreas)
  let collapsed = saved.collapsed
  let opacity = clampOpacity(saved.opacity)
  let lastState: LiveState | null = null
  let lastRemote: RemoteStatus | null = null
  let contentHeight: number | null = null
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
    transparent: true,
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
    window.webContents.send(CHANNELS.opacity, opacity)
    if (lastState) window.webContents.send(CHANNELS.state, lastState)
    if (lastRemote) window.webContents.send(CHANNELS.remoteState, lastRemote)
  }
  window.webContents.on('did-finish-load', () => {
    push()
    window.show()
  })

  const persist = () => {
    clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      saveState(stateFile, { bounds, collapsed, opacity })
    }, SAVE_DELAY_MS)
  }
  // Both events fire only for the user's own drag or resize, so this is the one place the
  // window's reported bounds are trusted; programmatic resizes work from the remembered bounds.
  const adoptUserBounds = () => {
    const current = window.getBounds()
    // While collapsed only the position is meaningful; the expanded size is kept as it was.
    bounds = collapsed ? { ...bounds, x: current.x, y: current.y } : current
    persist()
  }
  window.on('moved', adoptUserBounds)
  window.on('resized', adoptUserBounds)

  return {
    window,
    sendState(state) {
      lastState = state
      if (!window.isDestroyed()) window.webContents.send(CHANNELS.state, state)
    },
    sendRemote(status) {
      lastRemote = status
      if (!window.isDestroyed()) window.webContents.send(CHANNELS.remoteState, status)
    },
    toggleCollapse() {
      const current = window.getBounds()
      if (!collapsed) bounds = current
      collapsed = !collapsed
      // Expanding restores the height the content last asked for, not the stale saved one.
      if (!collapsed && contentHeight !== null) bounds = { ...bounds, height: contentHeight }
      window.setResizable(!collapsed)
      window.setBounds(collapsed ? { ...collapsedRect(), x: current.x, y: current.y } : { ...bounds, x: current.x, y: current.y })
      bounds = { ...bounds, x: current.x, y: current.y }
      saveState(stateFile, { bounds, collapsed, opacity })
      window.webContents.send(CHANNELS.collapsed, collapsed)
    },
    setOpacity(value) {
      opacity = clampOpacity(value)
      window.webContents.send(CHANNELS.opacity, opacity)
      saveState(stateFile, { bounds, collapsed, opacity })
    },
    setContentHeight(height) {
      // While collapsed the list is hidden, so the measurement is the pill's, not the content's.
      if (collapsed) return
      contentHeight = Math.max(PILL_HEIGHT, Math.ceil(height))
      // Only the height follows the content; position and width stay as the user left them.
      // Build the rect from the remembered bounds, not getBounds: on a display with fractional DPI
      // scaling each getBounds/setBounds round trip can grow the window by a pixel, which crept
      // outward (width included) as the height now changes both ways.
      bounds = { ...bounds, height: contentHeight }
      if (window.getBounds().height !== contentHeight) window.setBounds(bounds)
      persist()
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
