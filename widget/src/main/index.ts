import * as path from 'node:path'
import { app, ipcMain, Menu, nativeImage, net, protocol, Tray } from 'electron'
import { chimeFolder, pollLiveAndAfk, switchAfk } from './afk'
import { createApi } from './api'
import { BreakController } from './breakController'
import { BreakTimer, breakCountdown, DEFAULT_BREAK_MINUTES } from './breakTimer'
import { createBreakWindow } from './breakWindow'
import { loadConfig } from './config'
import { CHANNELS } from '../shared/ipc'
import { startPoller } from './poller'
import { loadProjects, PROJECTS_POLL_MS, ProjectsTooltip } from './projectsTooltip'
import { RemoteTooltip } from './remoteTooltip'
import type { RemoteStatus } from '../shared/types'
import { loadState } from './state'
import { Supervisor } from './supervisor'
import { createDeps } from './system'
import { TooltipSlot } from './tooltipSlot'
import { createTooltipWindow } from './tooltipWindow'
import { createWidgetWindow, type WidgetWindow } from './window'
import { registerWorkoutHandler, registerWorkoutScheme } from './workoutProtocol'
import { discoverWorkouts, workoutFolders } from './workouts'

const BREAK_TICK_MS = 1000
/** How often the break length is read from Settings, so a change reaches a count in progress. */
const BREAK_MINUTES_POLL_MS = 60_000

// One widget per user session: a second launch just brings the first one forward.
if (!app.requestSingleInstanceLock()) {
  app.quit()
} else {
  let widget: WidgetWindow | undefined
  app.on('second-instance', () => widget?.show())
  // The workout scheme must be privileged before the app is ready; its handler is added after.
  registerWorkoutScheme(protocol)

  void app.whenReady().then(() => {
    const config = loadConfig()
    const api = createApi(config.backendPort)
    const supervisor = new Supervisor(createDeps(config))
    const stateFile = path.join(app.getPath('userData'), 'widget-state.json')

    const win = createWidgetWindow(stateFile, loadState(stateFile))
    widget = win
    // The AFK flag is a local file, read on every poll beside /api/live, so the button works with the backend down.
    const chimes = chimeFolder()
    // The break count pauses while AFK is on; it reads the latest flag the poll below saw.
    let afkOn = false
    const poller = startPoller(
      () => pollLiveAndAfk(() => api.fetchLive(), chimes),
      ({ live, afk }) => {
        afkOn = afk.on
        win.sendState(live)
        win.sendAfk(afk)
      },
    )

    // The break timer counts work time; the break window is its own window and the list window is
    // never touched. Closing the break window restarts the count.
    const folders = workoutFolders(config.repoRoot)
    registerWorkoutHandler(protocol, net, folders)
    const breakTimer = new BreakTimer()
    const breaks = new BreakController({
      scan: () => discoverWorkouts(folders),
      openWindow: createBreakWindow,
      onClosed: () => breakTimer.reset(),
    })
    let breakMinutes = DEFAULT_BREAK_MINUTES
    const breakMinutesPoller = startPoller(() => api.fetchBreakMinutes(), (minutes) => (breakMinutes = minutes), BREAK_MINUTES_POLL_MS)
    const pushCountdown = () => win.sendBreakCountdown(breakCountdown(breakTimer, afkOn, breakMinutes, breaks.isOpen))
    const breakTick = setInterval(() => {
      breakTimer.tick(afkOn, breakMinutes)
      if (breakTimer.due) breaks.open()
      pushCountdown()
    }, BREAK_TICK_MS)
    // Seed the value so a page that finishes loading before the first tick is not blank.
    pushCountdown()

    // Remote mode is the backend's to run; the widget only shows it and asks for it on or off.
    let remote: RemoteStatus = { state: 'unavailable' }
    const tooltipWindow = createTooltipWindow()
    // The Remote button and the Ledger button each have a tooltip; they share this one window.
    const slot = new TooltipSlot((content) =>
      content ? tooltipWindow.show(content, win.window.getBounds()) : tooltipWindow.hide(),
    )
    const tooltip = new RemoteTooltip({
      fetchQr: () => api.fetchQr(),
      present: (content) => slot.present('remote', content),
      now: Date.now,
    })
    // Read at startup, every minute, and on each hover, so a hover shows rows at once. The poller
    // never overlaps reads, and a hover during a read joins it.
    const projects = new ProjectsTooltip({
      present: (content) => slot.present('projects', content),
      refresh: () => void projectsPoller.refresh(),
    })
    const projectsPoller = startPoller(() => loadProjects(api), (data) => projects.onData(data), PROJECTS_POLL_MS)
    const applyRemote = (status: RemoteStatus) => {
      remote = status
      win.sendRemote(status)
      tooltip.onStatus(status)
    }
    const remotePoller = startPoller(() => api.fetchRemote(), applyRemote)

    // Cold start: bring up the backend if nothing answers. A backend that is already running is
    // adopted and, being not ours, is never stopped by Quit.
    void supervisor.ensureBackend()

    ipcMain.handle(CHANNELS.openSession, async (_event, sessionId: unknown) => {
      if (typeof sessionId !== 'string') return 'failed'
      const result = await api.openRepo(sessionId)
      if (result === 'ended') void poller.refresh()
      return result
    })
    ipcMain.on(CHANNELS.setRemote, (_event, enabled: unknown) => {
      if (typeof enabled !== 'boolean') return
      void api.setRemoteMode(enabled).then((status) => {
        applyRemote(status)
        void remotePoller.refresh()
      })
    })
    ipcMain.handle(CHANNELS.setAutoApprove, async (_event, sessionId: unknown, enabled: unknown) => {
      if (typeof sessionId !== 'string' || typeof enabled !== 'boolean') return false
      const ok = await api.setAutoApprove(sessionId, enabled)
      void poller.refresh()
      return ok
    })
    ipcMain.handle(CHANNELS.setAfk, async (_event, enabled: unknown) => {
      if (typeof enabled !== 'boolean') return false
      const ok = await switchAfk(chimes, enabled, () => api.fetchAfkMinutes())
      void poller.refresh()
      return ok
    })
    ipcMain.on(CHANNELS.remoteHover, (_event, hovering: unknown) => {
      if (typeof hovering === 'boolean') tooltip.setHover(hovering)
    })
    ipcMain.on(CHANNELS.ledgerHover, (_event, hovering: unknown) => {
      if (typeof hovering === 'boolean') projects.setHover(hovering)
    })
    ipcMain.on(CHANNELS.openLedger, () => void supervisor.openLedger())
    ipcMain.on(CHANNELS.setOpacity, (_event, value: unknown) => {
      if (typeof value === 'number') win.setOpacity(value)
    })
    ipcMain.on(CHANNELS.setContentHeight, (_event, value: unknown) => {
      if (typeof value === 'number' && Number.isFinite(value)) win.setContentHeight(value)
    })
    ipcMain.on(CHANNELS.toggleCollapse, () => win.toggleCollapse())
    ipcMain.on(CHANNELS.breakStart, () => breaks.start())
    ipcMain.on(CHANNELS.breakSkip, () => breaks.skip())
    ipcMain.on(CHANNELS.breakClose, () => breaks.close())
    ipcMain.on(CHANNELS.breakFinished, () => breaks.finished())

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

    // Quitting kills a backend this widget started, and Remote mode would die with it while its
    // gateway container kept running. So close Remote mode first, then stop what we started.
    let quitting = false
    app.on('before-quit', (event) => {
      poller.stop()
      remotePoller.stop()
      projectsPoller.stop()
      breakMinutesPoller.stop()
      clearInterval(breakTick)
      tooltip.dispose()
      projects.dispose()
      tooltipWindow.destroy()
      const remoteActive = remote.state === 'starting' || remote.state === 'ready'
      if (!quitting && remoteActive && supervisor.ownedNames().includes('backend')) {
        quitting = true
        event.preventDefault()
        void api.setRemoteMode(false).finally(() => {
          supervisor.stopOwned()
          app.quit()
        })
        return
      }
      supervisor.stopOwned()
    })
  })

  // The window has no close button; if it is ever closed, quit rather than leave an invisible process.
  app.on('window-all-closed', () => app.quit())
}
