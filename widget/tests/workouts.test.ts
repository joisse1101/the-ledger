import * as fs from 'node:fs'
import * as os from 'node:os'
import * as path from 'node:path'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  DEFAULT_IMAGE_SECONDS,
  discoverWorkouts,
  PERSONAL_WORKOUTS_RELATIVE_PATH,
  WORKOUT_YAML,
  workoutFolders,
  type WorkoutFolders,
} from '../src/main/workouts'

let temp: string
let folders: WorkoutFolders

const touch = (...parts: string[]) => {
  const file = path.join(temp, ...parts)
  fs.mkdirSync(path.dirname(file), { recursive: true })
  fs.writeFileSync(file, 'x')
  return file
}
const write = (text: string, ...parts: string[]) => {
  const file = path.join(temp, ...parts)
  fs.mkdirSync(path.dirname(file), { recursive: true })
  fs.writeFileSync(file, text)
  return file
}
const names = (workouts: Array<{ name: string }>) => workouts.map((w) => w.name).sort()

beforeEach(() => {
  temp = fs.mkdtempSync(path.join(os.tmpdir(), 'ledger-workouts-'))
  folders = { starter: path.join(temp, 'starter'), personal: path.join(temp, 'mine') }
  fs.mkdirSync(folders.starter)
  fs.mkdirSync(folders.personal)
})

afterEach(() => {
  fs.rmSync(temp, { recursive: true })
})

describe('discoverWorkouts', () => {
  it('finds a video file as a workout named after the file', () => {
    touch('mine', 'neck roll.mp4')
    touch('mine', 'notes.txt')
    const { workouts, notes } = discoverWorkouts(folders)
    expect(workouts).toEqual([
      { id: 'mine/neck roll.mp4', name: 'neck roll', root: 'mine', kind: 'video', file: 'neck roll.mp4' },
    ])
    expect(notes).toEqual([])
  })

  it('finds an image folder, generating a YAML in natural order with 20 seconds each', () => {
    for (const file of ['10.png', '2.png', '1.png']) touch('mine', 'stretch', file)
    const { workouts } = discoverWorkouts(folders)
    expect(workouts).toHaveLength(1)
    expect(workouts[0]).toMatchObject({ name: 'stretch', root: 'mine', kind: 'images' })
    const images = (workouts[0] as { images: Array<{ file: string; seconds: number }> }).images
    expect(images).toEqual(
      ['1.png', '2.png', '10.png'].map((file) => ({ file: `stretch/${file}`, seconds: DEFAULT_IMAGE_SECONDS })),
    )
    const generated = fs.readFileSync(path.join(folders.personal, 'stretch', WORKOUT_YAML), 'utf8')
    expect(generated.indexOf('1.png')).toBeLessThan(generated.indexOf('2.png'))
    expect(generated.indexOf('2.png')).toBeLessThan(generated.indexOf('10.png'))
    expect(DEFAULT_IMAGE_SECONDS).toBe(20)
  })

  it('leaves an existing YAML untouched and follows its order and seconds', () => {
    touch('mine', 's', 'a.svg')
    touch('mine', 's', 'b.svg')
    const text = '# mine\nimages:\n  - {file: b.svg, seconds: 10}\n  - {file: a.svg, seconds: 30}\n'
    const yamlFile = write(text, 'mine', 's', WORKOUT_YAML)
    const { workouts } = discoverWorkouts(folders)
    discoverWorkouts(folders)
    expect(fs.readFileSync(yamlFile, 'utf8')).toBe(text)
    expect(workouts[0]).toMatchObject({
      images: [
        { file: 's/b.svg', seconds: 10 },
        { file: 's/a.svg', seconds: 30 },
      ],
    })
  })

  it('skips a broken YAML with a note and keeps the other workouts', () => {
    touch('mine', 'good', 'a.png')
    touch('mine', 'bad', 'a.png')
    write('images: [unclosed', 'mine', 'bad', WORKOUT_YAML)
    const { workouts, notes } = discoverWorkouts(folders)
    expect(names(workouts)).toEqual(['good'])
    expect(notes).toHaveLength(1)
    expect(notes[0]).toContain('mine/bad')
  })

  it.each([
    ['a parent-folder entry', '../../secret.png'],
    ['an absolute path', 'C:/Users/someone/photo.png'],
    ['a missing image', 'nope.png'],
  ])('rejects %s with a note', (_name, file) => {
    touch('secret.png')
    touch('mine', 's', 'a.png')
    write(`images:\n  - {file: "${file}", seconds: 5}\n`, 'mine', 's', WORKOUT_YAML)
    const { workouts, notes } = discoverWorkouts(folders)
    expect(workouts).toEqual([])
    expect(notes[0]).toContain('mine/s')
  })

  it.each([
    ['no seconds', '- {file: a.png}'],
    ['zero seconds', '- {file: a.png, seconds: 0}'],
    ['too many seconds', '- {file: a.png, seconds: 601}'],
    ['a non-image file', '- {file: notes.txt, seconds: 5}'],
  ])('rejects an entry with %s', (_name, entry) => {
    touch('mine', 's', 'a.png')
    touch('mine', 's', 'notes.txt')
    write(`images:\n  ${entry}\n`, 'mine', 's', WORKOUT_YAML)
    expect(discoverWorkouts(folders).workouts).toEqual([])
  })

  it('rejects an empty images list', () => {
    touch('mine', 's', 'a.png')
    write('images: []\n', 'mine', 's', WORKOUT_YAML)
    expect(discoverWorkouts(folders).workouts).toEqual([])
  })

  it('creates a missing personal folder and still uses the starter workouts', () => {
    fs.rmSync(folders.personal, { recursive: true })
    touch('starter', 'chin tuck', 'a.svg')
    write('images:\n  - {file: a.svg, seconds: 5}\n', 'starter', 'chin tuck', WORKOUT_YAML)
    const { workouts } = discoverWorkouts(folders)
    expect(fs.existsSync(folders.personal)).toBe(true)
    expect(names(workouts)).toEqual(['chin tuck'])
  })

  it('pools starter and personal workouts together', () => {
    touch('starter', 'one.mp4')
    touch('mine', 'two.mp4')
    expect(names(discoverWorkouts(folders).workouts)).toEqual(['one', 'two'])
  })

  it('writes nothing into the starter folder, even for an image folder with no YAML', () => {
    touch('starter', 'bare', 'a.svg')
    const { workouts, notes } = discoverWorkouts(folders)
    expect(workouts).toEqual([])
    expect(notes[0]).toContain('starter/bare')
    expect(fs.readdirSync(path.join(folders.starter, 'bare'))).toEqual(['a.svg'])
  })

  it('returns nothing and does not throw when both folders are missing', () => {
    const missing = { starter: path.join(temp, 'no-starter'), personal: path.join(temp, 'deep', 'no-mine') }
    expect(discoverWorkouts(missing).workouts).toEqual([])
  })

  it('leaves out a link that points outside the folder, with a note', () => {
    const outside = path.join(temp, 'outside')
    fs.mkdirSync(outside)
    fs.writeFileSync(path.join(outside, 'a.png'), 'x')
    fs.symlinkSync(outside, path.join(folders.personal, 'linked'), 'junction')
    const { workouts, notes } = discoverWorkouts(folders)
    expect(workouts).toEqual([])
    expect(notes[0]).toContain('mine/linked')
    expect(fs.existsSync(path.join(outside, WORKOUT_YAML))).toBe(false)
  })
})

describe('workoutFolders', () => {
  it('builds the personal folder from the pinned relative path and .gitignore lists it', () => {
    const repoRoot = path.resolve(__dirname, '..', '..')
    expect(PERSONAL_WORKOUTS_RELATIVE_PATH).toBe('widget/workouts/mine')
    expect(workoutFolders(repoRoot).personal).toBe(path.join(repoRoot, 'widget', 'workouts', 'mine'))
    const ignored = fs.readFileSync(path.join(repoRoot, '.gitignore'), 'utf8').split(/\r?\n/)
    expect(ignored).toContain(`${PERSONAL_WORKOUTS_RELATIVE_PATH}/`)
  })
})
