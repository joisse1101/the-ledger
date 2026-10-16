import * as path from 'node:path'
import { BrowserWindow, nativeTheme, screen } from 'electron'
import { CHANNELS } from '../shared/ipc'
import type { TooltipContent } from '../shared/types'
import { placeTooltip } from './remoteTooltip'
import type { Rect } from './state'

const MESSAGE_SIZE = { width: 220, height: 64 }
const QR_SIZE = { width: 220, height: 290 }

export interface TooltipWindow {
  /** Draws `content` next to `anchor` (the widget's bounds) without taking focus. */
  show(content: TooltipContent, anchor: Rect): void
  hide(): void
  destroy(): void
}

/**
 * The small window beside the widget that shows Remote mode's status and sign-in code. Frameless,
 * always on top, never focusable, ignoring the mouse (so it can't be stuck open or steal a click),
 * and no taskbar entry. It draws only what the main process sends it, in the same sandbox and
 * CSP as the widget. Created on first use and kept hidden between uses.
 */
export function createTooltipWindow(): TooltipWindow {
  let window: BrowserWindow | undefined
  let loaded = false
  let pending: TooltipContent | undefined

  const ensure = (): BrowserWindow => {
    if (window && !window.isDestroyed()) return window
    loaded = false
    const created = new BrowserWindow({
      ...MESSAGE_SIZE,
      frame: false,
      resizable: false,
      movable: false,
      focusable: false,
      skipTaskbar: true,
      alwaysOnTop: true,
      fullscreenable: false,
      maximizable: false,
      show: false,
      backgroundColor: nativeTheme.shouldUseDarkColors ? '#121214' : '#f3eef0',
      webPreferences: {
        preload: path.join(__dirname, '..', 'preload', 'tooltip.js'),
        contextIsolation: true,
        sandbox: true,
        nodeIntegration: false,
      },
    })
    created.setAlwaysOnTop(true, 'screen-saver')
    created.setIgnoreMouseEvents(true)
    created.setMenuBarVisibility(false)
    created.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
    created.webContents.on('will-navigate', (event) => event.preventDefault())
    created.webContents.on('did-finish-load', () => {
      loaded = true
      if (pending) created.webContents.send(CHANNELS.tooltip, pending)
    })
    void created.loadFile(path.join(__dirname, '..', 'ui', 'renderer', 'tooltip.html'))
    window = created
    return created
  }

  return {
    show(content, anchor) {
      const target = ensure()
      const size = content.kind === 'qr' ? QR_SIZE : MESSAGE_SIZE
      const workArea = screen.getDisplayMatching(anchor).workArea
      target.setBounds({ ...placeTooltip(anchor, size, workArea), ...size })
      pending = content
      if (loaded) target.webContents.send(CHANNELS.tooltip, content)
      if (!target.isVisible()) target.showInactive()
    },
    hide() {
      pending = undefined
      if (window && !window.isDestroyed() && window.isVisible()) window.hide()
    },
    destroy() {
      pending = undefined
      if (window && !window.isDestroyed()) window.destroy()
      window = undefined
    },
  }
}
