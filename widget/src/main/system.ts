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
    webDistExists: () => fs.existsSync(path.join(webDir, 'dist', 'index.html')),
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
