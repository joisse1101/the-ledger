import * as path from 'node:path'
import { BrowserWindow, nativeTheme } from 'electron'
import { CHANNELS } from '../shared/ipc'
import type { BreakState } from '../shared/types'
import type { BreakWindowHandle } from './breakController'

const BREAK_WINDOW_SIZE = { width: 560, height: 520 }

/**
 * The break window: focusable (its buttons take clicks) but shown with `showInactive`, so a stray
 * Space or Enter in another window cannot press Start. Frameless, always on top, sandboxed with
 * the page's own strict CSP, and destroyed on close. It sees workout files only through the
 * `ledger-workout:` scheme. `onClosed` runs if it is closed by the system rather than by `destroy`.
 */
export function createBreakWindow(onClosed: () => void): BreakWindowHandle {
  const window = new BrowserWindow({
    ...BREAK_WINDOW_SIZE,
    frame: false,
    resizable: false,
    fullscreenable: false,
    maximizable: false,
    minimizable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    show: false,
    backgroundColor: nativeTheme.shouldUseDarkColors ? '#121214' : '#f3eef0',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'breakWindow.js'),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      autoplayPolicy: 'no-user-gesture-required',
    },
  })
  window.setAlwaysOnTop(true, 'screen-saver')
  window.setMenuBarVisibility(false)
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  window.webContents.on('will-navigate', (event) => event.preventDefault())

  let loaded = false
  let latest: BreakState | undefined
  window.webContents.on('did-finish-load', () => {
    loaded = true
    if (latest) window.webContents.send(CHANNELS.breakState, latest)
  })
  window.on('closed', onClosed)
  window.once('ready-to-show', () => window.showInactive())
  void window.loadFile(path.join(__dirname, '..', 'ui', 'renderer', 'breakWindow.html'))

  return {
    send(state) {
      latest = state
      if (loaded && !window.isDestroyed()) window.webContents.send(CHANNELS.breakState, state)
    },
    destroy() {
      if (!window.isDestroyed()) window.destroy()
    },
  }
}
