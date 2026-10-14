import * as path from 'node:path'
import { app, ipcMain, Menu, nativeImage, Tray } from 'electron'
import { createApi } from './api'
import { loadConfig } from './config'
import { CHANNELS } from '../shared/ipc'
import { startPoller } from './poller'
import { loadState } from './state'
import { Supervisor } from './supervisor'
import { createDeps } from './system'
import { createWidgetWindow, type WidgetWindow } from './window'

// One widget per user session: a second launch just brings the first one forward.
if (!app.requestSingleInstanceLock()) {
  app.quit()
} else {
  let widget: WidgetWindow | undefined
  app.on('second-instance', () => widget?.show())

  void app.whenReady().then(() => {
    const config = loadConfig()
    const api = createApi(config.backendPort)
    const supervisor = new Supervisor(createDeps(config))
    const stateFile = path.join(app.getPath('userData'), 'widget-state.json')

    const win = createWidgetWindow(stateFile, loadState(stateFile))
    widget = win
    const poller = startPoller(() => api.fetchLive(), (state) => win.sendState(state))

    // Cold start: bring up the backend if nothing answers. A backend that is already running is
    // adopted and, being not ours, is never stopped by Quit.
    void supervisor.ensureBackend()

    ipcMain.handle(CHANNELS.openSession, async (_event, sessionId: unknown) => {
      if (typeof sessionId !== 'string') return 'failed'
      const result = await api.openRepo(sessionId)
      if (result === 'ended') void poller.refresh()
      return result
    })
    ipcMain.on(CHANNELS.openLedger, () => void supervisor.openLedger())
    ipcMain.on(CHANNELS.toggleCollapse, () => win.toggleCollapse())

    const tray = new Tray(nativeImage.createFromPath(path.join(__dirname, '..', '..', 'assets', 'tray.png')))
    tray.setToolTip('Ledger live sessions')
    const buildMenu = () =>
      Menu.buildFromTemplate([
        { label: 'Open Ledger', click: () => void supervisor.openLedger() },
        { label: 'Start backend', click: () => void supervisor.ensureBackend().then(() => poller.refresh()) },
        { label: win.isVisible() ? 'Hide widget' : 'Show widget', click: () => win.toggleVisible() },
        { type: 'separator' },
        { label: 'Quit', click: () => app.quit() },
      ])
    tray.on('click', () => win.show())
    tray.on('right-click', () => tray.popUpContextMenu(buildMenu()))

    app.on('before-quit', () => {
      poller.stop()
      supervisor.stopOwned()
    })
  })

  // The window has no close button; if it is ever closed, quit rather than leave an invisible process.
  app.on('window-all-closed', () => app.quit())
}
