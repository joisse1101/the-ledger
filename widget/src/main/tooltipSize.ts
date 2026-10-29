import type { TooltipContent } from '../shared/types'

export interface TooltipSize {
  width: number
  height: number
}

export const MESSAGE_SIZE: TooltipSize = { width: 220, height: 64 }
const QR_SIZE: TooltipSize = { width: 220, height: 290 }
const PROJECTS_WIDTH = 320
/** One line of the projects list: the heading, a project, or the "+N more" line. */
export const PROJECTS_LINE_HEIGHT = 20
/** The card's 10px padding and 1px border, top and bottom. */
const CARD_FRAME = 22

/** The window size `content` needs. The projects list is as tall as its lines, which the page draws
 *  at exactly `PROJECTS_LINE_HEIGHT` each. */
export function tooltipSize(content: TooltipContent): TooltipSize {
  switch (content.kind) {
    case 'message':
      return MESSAGE_SIZE
    case 'qr':
      return QR_SIZE
    case 'projects': {
      const lines = 1 + content.rows.length + (content.more > 0 ? 1 : 0)
      return { width: PROJECTS_WIDTH, height: CARD_FRAME + lines * PROJECTS_LINE_HEIGHT }
    }
  }
}
