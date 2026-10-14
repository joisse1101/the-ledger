/** IPC channel names. The sandboxed preload cannot import this file, so it repeats the literals;
 *  tests/ipc.test.ts fails if the two drift. */
export const CHANNELS = {
  state: 'widget:state',
  collapsed: 'widget:collapsed',
  openSession: 'widget:open-session',
  openLedger: 'widget:open-ledger',
  toggleCollapse: 'widget:toggle-collapse',
} as const
