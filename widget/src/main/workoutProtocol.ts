import * as path from 'node:path'
import { pathToFileURL } from 'node:url'
import type { Net, Protocol } from 'electron'
import { resolveInside } from './workoutPaths'
import type { WorkoutFolders, WorkoutRoot } from './workouts'

/** The scheme the break window loads workout files through: `ledger-workout://<root>/<path>`. */
export const WORKOUT_SCHEME = 'ledger-workout'

const ROOTS: readonly WorkoutRoot[] = ['starter', 'mine']
const isRoot = (value: string): value is WorkoutRoot => (ROOTS as readonly string[]).includes(value)

/** Must run before the app is ready. `stream` lets the video element seek. */
export function registerWorkoutScheme(protocol: Protocol): void {
  protocol.registerSchemesAsPrivileged([
    { scheme: WORKOUT_SCHEME, privileges: { standard: true, secure: true, stream: true, supportFetchAPI: true } },
  ])
}

/** The real path a workout URL names, or null when it is not one of the two roots, is malformed,
 *  or resolves outside its root. This is the only place a URL turns into a file path. */
export function resolveWorkoutUrl(url: string, folders: WorkoutFolders): string | null {
  let parsed: URL
  let relativePath: string
  try {
    parsed = new URL(url)
    relativePath = decodeURIComponent(parsed.pathname).replace(/^\/+/, '')
  } catch {
    return null
  }
  if (parsed.protocol !== `${WORKOUT_SCHEME}:` || !isRoot(parsed.hostname)) return null
  const rootDir = parsed.hostname === 'starter' ? folders.starter : folders.personal
  return resolveInside(path.resolve(rootDir), relativePath)
}

/** Serves workout files, answering 404 for anything outside the roots. The request's headers
 *  (notably `Range`) go on to the file read so the video element can seek. */
export function registerWorkoutHandler(protocol: Protocol, net: Net, folders: WorkoutFolders): void {
  protocol.handle(WORKOUT_SCHEME, (request) => {
    const file = resolveWorkoutUrl(request.url, folders)
    if (file === null) return new Response('Not found', { status: 404 })
    return net.fetch(pathToFileURL(file).toString(), { headers: request.headers })
  })
}
