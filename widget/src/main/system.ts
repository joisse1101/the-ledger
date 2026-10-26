import { spawn, spawnSync } from 'node:child_process'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { shell } from 'electron'
import { createApi } from './api'
import type { Config } from './config'
import type { Deps, SpawnSpec } from './supervisor'

const isUp = async (port: number): Promise<boolean> => {
  try {
    const response = await fetch(`http://127.0.0.1:${port}/`, { signal: AbortSignal.timeout(1500) })
    return response.status < 500
  } catch {
    return false
  }
}

const launch = (spec: SpawnSpec) =>
  spawn(spec.command, spec.args, {
    cwd: spec.cwd,
    env: { ...process.env, ...spec.env },
    shell: spec.shell,
    windowsHide: true,
    stdio: 'ignore',
  })

/** The newest modification time (ms) of any file under `target`, or 0 if it does not exist. */
const newestMtime = (target: string): number => {
  if (!fs.existsSync(target)) return 0
  const stat = fs.statSync(target)
  if (!stat.isDirectory()) return stat.mtimeMs
  return fs
    .readdirSync(target)
    .reduce((newest, name) => Math.max(newest, newestMtime(path.join(target, name))), 0)
}

/** The real OS-facing dependencies for the Supervisor. */
export function createDeps(config: Config): Deps {
  const apiDir = path.join(config.repoRoot, 'api')
  const webDir = path.join(config.repoRoot, 'web')
  const venvPython = path.join(apiDir, '.venv', 'Scripts', 'python.exe')
  const api = createApi(config.backendPort)
  return {
    spawn(spec) {
      const child = launch(spec)
      return { pid: child.pid, onExit: (callback) => void child.once('exit', callback) }
    },
    run: (spec) =>
      new Promise<boolean>((resolve) => {
        const child = launch(spec)
        child.once('error', () => resolve(false))
        child.once('exit', (code) => resolve(code === 0))
      }),
    backendUp: () => api.backendUp(),
    frontendUp: () => isUp(config.frontendPort),
    webBuildStale() {
      const builtAt = newestMtime(path.join(webDir, 'dist', 'index.html'))
      if (builtAt === 0) return true
      const sources = ['src', 'index.html', 'package.json'].map((name) => path.join(webDir, name))
      return Math.max(...sources.map(newestMtime)) > builtAt
    },
    killTree(pid) {
      spawnSync('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' })
    },
    openBrowser: (url) => void shell.openExternal(url),
    sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
    paths: { apiDir, webDir, python: fs.existsSync(venvPython) ? venvPython : 'python' },
    backendPort: config.backendPort,
    frontendPort: config.frontendPort,
  }
}
