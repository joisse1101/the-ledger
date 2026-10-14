import type { WidgetBridge } from '../shared/types'
import { mount } from './app.js'

declare global {
  interface Window {
    widget: WidgetBridge
  }
}

mount(document, window.widget)
