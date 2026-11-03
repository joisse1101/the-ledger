import * as fs from 'node:fs'
import * as path from 'node:path'
import { parse, stringify } from 'yaml'
import { resolveInside } from './workoutPaths'

/** The two folders a workout can come from; the URL scheme uses the same names. */
export type WorkoutRoot = 'starter' | 'mine'

export interface WorkoutImage {
  /** Path beneath the workout's root folder, with forward slashes. */
  file: string
  seconds: number
}

export type Workout =
  | { id: string; name: string; root: WorkoutRoot; kind: 'video'; file: string }
  | { id: string; name: string; root: WorkoutRoot; kind: 'images'; images: WorkoutImage[] }

export interface WorkoutScan {
  workouts: Workout[]
  /** One short line per workout that was left out, naming it and the reason. */
  notes: string[]
}

export interface WorkoutFolders {
  starter: string
  personal: string
}

/** The personal folder, relative to the repo root. The backend repeats this string; a test pins both. */
export const PERSONAL_WORKOUTS_RELATIVE_PATH = 'widget/workouts/mine'
export const STARTER_WORKOUTS_RELATIVE_PATH = 'widget/workouts/starter'
export const WORKOUT_YAML = 'workout.yaml'
export const DEFAULT_IMAGE_SECONDS = 20
export const MAX_IMAGE_SECONDS = 600

const VIDEO_EXTENSIONS = new Set(['.mp4', '.webm', '.m4v', '.ogv', '.mov'])
const IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'])

const extensionOf = (file: string): string => path.extname(file).toLowerCase()
const naturalOrder = (a: string, b: string): number => a.localeCompare(b, undefined, { numeric: true })

/** The widget's two folders under the repo root. */
export const workoutFolders = (repoRoot: string): WorkoutFolders => ({
  starter: path.join(repoRoot, ...STARTER_WORKOUTS_RELATIVE_PATH.split('/')),
  personal: path.join(repoRoot, ...PERSONAL_WORKOUTS_RELATIVE_PATH.split('/')),
})

type ImagesResult = { images: WorkoutImage[] } | { reason: string }

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

/** Checks the parsed YAML by hand: a non-empty `images` list of existing files inside the
 *  workout's folder, each with 1 to 600 seconds. */
function validateImages(parsed: unknown, rootDir: string, folderName: string): ImagesResult {
  if (!isRecord(parsed) || !Array.isArray(parsed.images) || parsed.images.length === 0) {
    return { reason: 'images must be a non-empty list' }
  }
  const folderDir = path.join(rootDir, folderName)
  const realRoot = fs.realpathSync(rootDir)
  const images: WorkoutImage[] = []
  for (const [index, entry] of parsed.images.entries()) {
    const position = `image ${index + 1}`
    if (!isRecord(entry) || typeof entry.file !== 'string') return { reason: `${position} has no file` }
    const { file, seconds } = entry
    if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds <= 0 || seconds > MAX_IMAGE_SECONDS) {
      return { reason: `${position} needs seconds above 0 and up to ${MAX_IMAGE_SECONDS}` }
    }
    const real = resolveInside(folderDir, file)
    if (real === null) return { reason: `${position} (${file}) is missing or outside the folder` }
    if (!fs.statSync(real).isFile() || !IMAGE_EXTENSIONS.has(extensionOf(real))) {
      return { reason: `${position} (${file}) is not an image` }
    }
    images.push({ file: path.relative(realRoot, real).split(path.sep).join('/'), seconds })
  }
  return { images }
}

/** Writes a YAML file listing the images in natural file-name order. The `wx` flag makes the
 *  write fail rather than replace a file that is already there, even when two writers race. */
function generateYaml(folderDir: string, imageFiles: string[]): void {
  const sorted = [...imageFiles].sort(naturalOrder)
  const text = stringify({ images: sorted.map((file) => ({ file, seconds: DEFAULT_IMAGE_SECONDS })) })
  try {
    fs.writeFileSync(path.join(folderDir, WORKOUT_YAML), text, { encoding: 'utf8', flag: 'wx' })
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error
  }
}

function readImageWorkout(rootDir: string, root: WorkoutRoot, folderName: string, mayGenerate: boolean): Workout | string {
  const folderDir = path.join(rootDir, folderName)
  const yamlPath = path.join(folderDir, WORKOUT_YAML)
  if (!fs.existsSync(yamlPath)) {
    const imageFiles = fs.readdirSync(folderDir).filter((file) => IMAGE_EXTENSIONS.has(extensionOf(file)))
    if (imageFiles.length === 0) return 'has no images'
    if (!mayGenerate) return `has no ${WORKOUT_YAML}`
    generateYaml(folderDir, imageFiles)
  }
  let parsed: unknown
  try {
    parsed = parse(fs.readFileSync(yamlPath, 'utf8'))
  } catch (error) {
    return `${WORKOUT_YAML} cannot be read: ${(error as Error).message.split('\n')[0]}`
  }
  const result = validateImages(parsed, rootDir, folderName)
  if ('reason' in result) return result.reason
  return { id: `${root}/${folderName}`, name: folderName, root, kind: 'images', images: result.images }
}

/** Reads one folder. Only the personal folder may get a generated YAML file. */
function scanFolder(rootDir: string, root: WorkoutRoot, mayGenerate: boolean, scan: WorkoutScan): void {
  if (!fs.existsSync(rootDir)) return
  const entries = fs.readdirSync(rootDir, { withFileTypes: true }).sort((a, b) => naturalOrder(a.name, b.name))
  for (const entry of entries) {
    if (resolveInside(rootDir, entry.name) === null) {
      scan.notes.push(`${root}/${entry.name}: points outside the workouts folder`)
      continue
    }
    if (entry.isDirectory() || (entry.isSymbolicLink() && fs.statSync(path.join(rootDir, entry.name)).isDirectory())) {
      try {
        const found = readImageWorkout(rootDir, root, entry.name, mayGenerate)
        if (typeof found === 'string') scan.notes.push(`${root}/${entry.name}: ${found}`)
        else scan.workouts.push(found)
      } catch (error) {
        scan.notes.push(`${root}/${entry.name}: cannot be read: ${(error as Error).message}`)
      }
    } else if (VIDEO_EXTENSIONS.has(extensionOf(entry.name))) {
      const name = path.basename(entry.name, path.extname(entry.name))
      scan.workouts.push({ id: `${root}/${entry.name}`, name, root, kind: 'video', file: entry.name })
    }
  }
}

/**
 * Every valid workout in the starter and personal folders. A missing personal folder is created;
 * nothing is ever written into the starter folder. A workout that cannot be used is left out
 * with a note, and a folder that cannot be read never throws.
 */
export function discoverWorkouts(folders: WorkoutFolders): WorkoutScan {
  const scan: WorkoutScan = { workouts: [], notes: [] }
  try {
    fs.mkdirSync(folders.personal, { recursive: true })
  } catch (error) {
    scan.notes.push(`mine: folder cannot be created: ${(error as Error).message}`)
  }
  const sources: Array<[string, WorkoutRoot, boolean]> = [
    [folders.starter, 'starter', false],
    [folders.personal, 'mine', true],
  ]
  for (const [dir, root, mayGenerate] of sources) {
    try {
      scanFolder(dir, root, mayGenerate, scan)
    } catch (error) {
      scan.notes.push(`${root}: folder cannot be read: ${(error as Error).message}`)
    }
  }
  return scan
}
