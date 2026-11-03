import type { BreakState, BreakWorkout } from '../shared/types'

export interface BreakActions {
  start(): void
  skip(): void
  close(): void
  finished(): void
}

const NO_WORKOUTS_NOTE = 'There are no workouts to show. Add a video or a folder of images to the personal workouts folder.'
const UNPLAYABLE_NOTE = 'This video cannot be played. You can skip it or close this window.'
const MS_PER_SECOND = 1000

const el = <K extends keyof HTMLElementTagNameMap>(
  doc: Document,
  tag: K,
  className: string,
  text?: string,
): HTMLElementTagNameMap[K] => {
  const node = doc.createElement(tag)
  node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

/**
 * Draws the break page from the one state message the main process sends. A video plays through
 * the `<video>` element; images are stepped here with a timer for each one's seconds, and the
 * main process is told when the last one ends. Every value is set as text or as an element
 * attribute, never as markup. `render` replaces the page, so a new state stops the old timer.
 */
export function createBreakView(root: HTMLElement, actions: BreakActions) {
  const doc = root.ownerDocument
  let timer: ReturnType<typeof setTimeout> | undefined

  const button = (label: string, onClick: () => void, primary = false): HTMLButtonElement => {
    const node = el(doc, 'button', primary ? 'button primary' : 'button', label)
    node.type = 'button'
    node.addEventListener('click', onClick)
    return node
  }

  const video = (workout: Extract<BreakWorkout, { kind: 'video' }>, stage: HTMLElement): void => {
    const player = el(doc, 'video', 'media')
    player.src = workout.src
    player.controls = true
    player.autoplay = true
    player.addEventListener('ended', () => actions.finished())
    player.addEventListener('error', () => {
      player.remove()
      stage.append(el(doc, 'p', 'note', UNPLAYABLE_NOTE))
    })
    stage.append(player)
  }

  const images = (workout: Extract<BreakWorkout, { kind: 'images' }>, stage: HTMLElement): void => {
    const picture = el(doc, 'img', 'media')
    picture.alt = workout.name
    const caption = el(doc, 'p', 'hint')
    stage.append(picture, caption)
    const show = (index: number): void => {
      const image = workout.images[index]
      picture.src = image.src
      caption.textContent = `${index + 1} of ${workout.images.length}`
      timer = setTimeout(() => {
        if (index + 1 < workout.images.length) show(index + 1)
        else actions.finished()
      }, image.seconds * MS_PER_SECOND)
    }
    show(0)
  }

  const render = (state: BreakState): void => {
    clearTimeout(timer)
    root.replaceChildren()
    const { workout, stage: phase } = state

    const top = el(doc, 'div', 'top')
    const heading = el(doc, 'div', 'heading')
    heading.append(el(doc, 'p', 'eyebrow', 'Time for a break'))
    heading.append(el(doc, 'h1', 'title', workout ? workout.name : 'No workouts'))
    top.append(heading)
    top.append(button('Close', actions.close))

    const stage = el(doc, 'div', 'stage')
    if (!workout) {
      stage.append(el(doc, 'p', 'note', NO_WORKOUTS_NOTE))
    } else if (phase === 'idle') {
      stage.append(el(doc, 'p', 'hint', 'Press Start when you are ready.'))
    } else if (phase === 'finished') {
      stage.append(el(doc, 'p', 'hint', 'Done. Close this window, or play it again.'))
    } else if (workout.kind === 'video') {
      video(workout, stage)
    } else {
      images(workout, stage)
    }
    if (state.notes.length > 0) {
      const problems = el(doc, 'ul', 'problems')
      for (const note of state.notes) problems.append(el(doc, 'li', 'problem', note))
      stage.append(problems)
    }

    const bar = el(doc, 'div', 'actions')
    if (workout) {
      bar.append(button('Skip', actions.skip))
      if (phase !== 'playing') bar.append(button(phase === 'finished' ? 'Play again' : 'Start', actions.start, true))
    }
    root.append(top, stage, bar)
  }

  return { render }
}
