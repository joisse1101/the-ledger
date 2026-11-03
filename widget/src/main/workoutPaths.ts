import * as fs from 'node:fs'
import * as path from 'node:path'

const DRIVE_PREFIX = /^[a-zA-Z]:/

/** Whether `child` is `root` or lies beneath it; both must already be real paths. */
function isInside(root: string, child: string): boolean {
  const relative = path.relative(root, child)
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative))
}

/**
 * The real path of `relativePath` beneath `root`, or null when it is absolute, climbs out with
 * `..`, does not exist, or resolves (through a link) to somewhere outside `root`.
 * Looking at the real path is what catches a link that leaves the folder.
 */
export function resolveInside(root: string, relativePath: string): string | null {
  if (!relativePath || path.isAbsolute(relativePath) || DRIVE_PREFIX.test(relativePath)) return null
  try {
    const realRoot = fs.realpathSync(root)
    const realTarget = fs.realpathSync(path.resolve(realRoot, relativePath))
    return isInside(realRoot, realTarget) ? realTarget : null
  } catch {
    // A missing root or file is the same answer as an outside one: nothing to serve.
    return null
  }
}
