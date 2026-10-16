import { contextBridge, ipcRenderer } from 'electron'
import type { TooltipBridge, TooltipContent } from '../shared/types'

// Channel name repeated from shared/ipc.ts (a sandboxed preload cannot import it);
// tests/ipc.test.ts fails if the two drift.
const bridge: TooltipBridge = {
  onContent: (callback) => {
    ipcRenderer.on('widget:tooltip', (_event, content: TooltipContent) => callback(content))
  },
}

contextBridge.exposeInMainWorld('tooltip', bridge)
