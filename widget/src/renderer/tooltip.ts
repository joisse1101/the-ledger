import type { TooltipBridge } from '../shared/types'
import { renderTooltip } from './tooltipView.js'

declare global {
  interface Window {
    tooltip: TooltipBridge
  }
}

const card = document.getElementById('card') as HTMLElement
window.tooltip.onContent((content) => renderTooltip(card, content))
