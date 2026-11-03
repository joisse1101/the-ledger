import * as fs from 'node:fs'
import * as os from 'node:os'
import * as path from 'node:path'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { discoverWorkouts, workoutFolders, WORKOUT_YAML } from '../src/main/workouts'

const REPO_ROOT = path.resolve(__dirname, '..', '..')
const STARTER_DIR = workoutFolders(REPO_ROOT).starter
const MIN_STARTERS = 6
const MAX_STARTERS = 8

let temp: string

beforeEach(() => {
  temp = fs.mkdtempSync(path.join(os.tmpdir(), 'ledger-starters-'))
})

afterEach(() => {
  fs.rmSync(temp, { recursive: true })
})

/** Runs the widget's own discovery on a starter folder, with an empty personal folder in the temp dir. */
const scan = (starter: string) => discoverWorkouts({ starter, personal: path.join(temp, 'mine') })

const starterFolders = () =>
  fs.readdirSync(STARTER_DIR, { withFileTypes: true }).filter((entry) => entry.isDirectory()).map((e) => e.name)

describe('starter workouts', () => {
  it('ships six to eight folders, each with its own workout.yaml', () => {
    const folders = starterFolders()
    expect(folders.length).toBeGreaterThanOrEqual(MIN_STARTERS)
    expect(folders.length).toBeLessThanOrEqual(MAX_STARTERS)
    for (const folder of folders) {
      expect(fs.existsSync(path.join(STARTER_DIR, folder, WORKOUT_YAML)), folder).toBe(true)
    }
  })

  it('loads every starter folder through the widget validator with four to six frames', () => {
    const { workouts, notes } = scan(STARTER_DIR)
    expect(notes).toEqual([])
    expect(workouts.map((w) => w.name).sort()).toEqual(starterFolders().sort())
    for (const workout of workouts) {
      expect(workout.root).toBe('starter')
      expect(workout.kind).toBe('images')
      const frames = workout.kind === 'images' ? workout.images.length : 0
      expect(frames, workout.name).toBeGreaterThanOrEqual(4)
      expect(frames, workout.name).toBeLessThanOrEqual(6)
    }
  })

  it('has SVG frames that are plain shapes with no script or external reference', () => {
    for (const folder of starterFolders()) {
      for (const file of fs.readdirSync(path.join(STARTER_DIR, folder)).filter((f) => f.endsWith('.svg'))) {
        const text = fs.readFileSync(path.join(STARTER_DIR, folder, file), 'utf8')
        const label = `${folder}/${file}`
        expect(text, label).toContain('viewBox=')
        expect(text.toLowerCase(), label).not.toContain('<script')
        expect(text, label).not.toMatch(/href=|url\(|@import|<image|foreignObject|https?:\/\/(?!www\.w3\.org\/2000\/svg)/)
      }
    }
  })

  it('leaves out a starter whose YAML points at a missing image, with a note', () => {
    const copy = path.join(temp, 'starter')
    fs.cpSync(STARTER_DIR, copy, { recursive: true })
    const broken = starterFolders()[0]
    const yamlFile = path.join(copy, broken, WORKOUT_YAML)
    fs.writeFileSync(yamlFile, 'images:\n  - {file: missing.svg, seconds: 20}\n')

    const { workouts, notes } = scan(copy)

    expect(workouts.map((w) => w.name)).not.toContain(broken)
    expect(workouts).toHaveLength(starterFolders().length - 1)
    expect(notes).toHaveLength(1)
    expect(notes[0]).toContain(`starter/${broken}`)
  })
})
