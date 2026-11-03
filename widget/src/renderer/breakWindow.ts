import type { BreakBridge } from '../shared/types'
import { createBreakView } from './breakView.js'

declare global {
  interface Window {
    breakWindow: BreakBridge
  }
}

const root = document.getElementById('break') as HTMLElement
const bridge = window.breakWindow
const view = createBreakView(root, {
  start: () => bridge.start(),
  skip: () => bridge.skip(),
  close: () => bridge.close(),
  finished: () => bridge.finished(),
})
bridge.onState((state) => view.render(state))
