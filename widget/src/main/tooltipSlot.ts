import type { TooltipContent } from '../shared/types'

export type TooltipSource = 'remote' | 'projects'

/**
 * The one tooltip window, shared by the Remote status tooltip and the projects tooltip. Each source
 * says what it has to show, and the slot draws the most recently presented content. A source that
 * has nothing no longer hides the window while another still has content, so Remote mode's code
 * popping up and going away never takes the projects list with it. Pure: drawing is injected.
 */
export class TooltipSlot {
  // A Map iterates in insertion order, and a source is removed before it is set again, so the last
  // value is always the most recently presented one.
  private readonly contents = new Map<TooltipSource, TooltipContent>()

  constructor(private readonly draw: (content: TooltipContent | null) => void) {}

  /** `source` now shows `content`, or nothing for null. */
  present(source: TooltipSource, content: TooltipContent | null): void {
    this.contents.delete(source)
    if (content) this.contents.set(source, content)
    this.draw([...this.contents.values()].at(-1) ?? null)
  }
}
