/** IPC channel names. The sandboxed preload cannot import this file, so it repeats the literals;
 *  tests/ipc.test.ts fails if the two drift. */
export const CHANNELS = {
  state: 'widget:state',
  collapsed: 'widget:collapsed',
  openSession: 'widget:open-session',
  openLedger: 'widget:open-ledger',
  toggleCollapse: 'widget:toggle-collapse',
  opacity: 'widget:opacity',
  setOpacity: 'widget:set-opacity',
  setContentHeight: 'widget:set-content-height',
  remoteState: 'widget:remote-state',
  setRemote: 'widget:set-remote',
  ledgerHover: 'widget:ledger-hover',
} as const
