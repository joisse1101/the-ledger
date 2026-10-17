import { contextBridge, ipcRenderer } from 'electron'
import type { LiveState, OpenRepoResult, RemoteStatus, WidgetBridge } from '../shared/types'

// A sandboxed preload cannot require local files, so the channel names are repeated here from
// shared/ipc.ts; tests/ipc.test.ts fails if they drift.
const bridge: WidgetBridge = {
  onState: (callback) => {
    ipcRenderer.on('widget:state', (_event, state: LiveState) => callback(state))
  },
  onCollapsed: (callback) => {
    ipcRenderer.on('widget:collapsed', (_event, collapsed: boolean) => callback(collapsed))
  },
  onOpacity: (callback) => {
    ipcRenderer.on('widget:opacity', (_event, opacity: number) => callback(opacity))
  },
  onRemote: (callback) => {
    ipcRenderer.on('widget:remote-state', (_event, status: RemoteStatus) => callback(status))
  },
  setRemote: (enabled) => ipcRenderer.send('widget:set-remote', enabled),
  setAutoApprove: (sessionId, enabled): Promise<boolean> =>
    ipcRenderer.invoke('widget:set-auto-approve', sessionId, enabled),
  ledgerHover: (hovering) => ipcRenderer.send('widget:ledger-hover', hovering),
  setOpacity: (opacity) => ipcRenderer.send('widget:set-opacity', opacity),
  setContentHeight: (height) => ipcRenderer.send('widget:set-content-height', height),
  openSession: (sessionId): Promise<OpenRepoResult> => ipcRenderer.invoke('widget:open-session', sessionId),
  openLedger: () => ipcRenderer.send('widget:open-ledger'),
  toggleCollapse: () => ipcRenderer.send('widget:toggle-collapse'),
}

contextBridge.exposeInMainWorld('widget', bridge)
