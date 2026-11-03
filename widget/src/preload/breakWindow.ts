import { contextBridge, ipcRenderer } from 'electron'
import type { BreakBridge, BreakState } from '../shared/types'

// Channel names repeated from shared/ipc.ts (a sandboxed preload cannot import it);
// tests/ipc.test.ts fails if the two drift.
const bridge: BreakBridge = {
  onState: (callback) => {
    ipcRenderer.on('widget:break-state', (_event, state: BreakState) => callback(state))
  },
  start: () => ipcRenderer.send('widget:break-start'),
  skip: () => ipcRenderer.send('widget:break-skip'),
  close: () => ipcRenderer.send('widget:break-close'),
  finished: () => ipcRenderer.send('widget:break-finished'),
}

contextBridge.exposeInMainWorld('breakWindow', bridge)
