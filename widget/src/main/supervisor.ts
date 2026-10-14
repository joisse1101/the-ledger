/**
 * Starts the backend and frontend hidden and remembers only the processes it started itself, so
 * quitting stops exactly those and never something the user (or Start-Ledger.ps1) already had
 * running. Everything touching the OS is injected through `Deps`, so tests use fakes. The gateway
 * and Docker are deliberately absent from this module.
 */

export interface Child {
  pid: number | undefined
  onExit(callback: () => void): void
}

export interface SpawnSpec {
  command: string
  args: string[]
  cwd: string
  env?: Record<string, string>
  /** Run through the shell (needed for `npm`, which is a .cmd on Windows). */
  shell?: boolean
}

export interface Deps {
  spawn(spec: SpawnSpec): Child
  /** Runs a command to completion; true on exit code 0. */
  run(spec: SpawnSpec): Promise<boolean>
  backendUp(): Promise<boolean>
  frontendUp(): Promise<boolean>
  webDistExists(): boolean
  /** Kills a pid and its whole process tree. */
  killTree(pid: number): void
  openBrowser(url: string): void
  sleep(ms: number): Promise<void>
  /** Where to find things; see config.ts. */
  paths: { apiDir: string; webDir: string; python: string }
  backendPort: number
  frontendPort: number
}

export type EnsureResult = 'already-running' | 'starting' | 'started' | 'failed'

const FRONTEND_WAIT_ATTEMPTS = 60
const FRONTEND_WAIT_MS = 500

export class Supervisor {
  private owned = new Map<'backend' | 'frontend', Child>()

  constructor(private readonly deps: Deps) {}

  /** The names of the processes this widget started and still believes are running. */
  ownedNames(): string[] {
    return [...this.owned.keys()]
  }

  async ensureBackend(): Promise<EnsureResult> {
    if (this.owned.has('backend')) return 'starting'
    if (await this.deps.backendUp()) return 'already-running'
    const { deps } = this
    this.track(
      'backend',
      deps.spawn({
        command: deps.paths.python,
        args: ['server.py', '--port', String(deps.backendPort), '--frontend-port', String(deps.frontendPort)],
        cwd: deps.paths.apiDir,
      }),
    )
    return 'started'
  }

  /** Makes sure the frontend answers, building first only if there is no build, then opens it. */
  async openLedger(): Promise<EnsureResult> {
    const { deps } = this
    const url = `http://localhost:${deps.frontendPort}`
    if (await deps.frontendUp()) {
      deps.openBrowser(url)
      return 'already-running'
    }
    if (!this.owned.has('frontend')) {
      const env = { BACKEND_PORT: String(deps.backendPort) }
      if (!deps.webDistExists()) {
        const built = await deps.run({ command: 'npm', args: ['run', 'build'], cwd: deps.paths.webDir, env, shell: true })
        if (!built) return 'failed'
      }
      this.track(
        'frontend',
        deps.spawn({
          command: 'npm',
          args: ['run', 'preview', '--', '--port', String(deps.frontendPort)],
          cwd: deps.paths.webDir,
          env,
          shell: true,
        }),
      )
    }
    for (let attempt = 0; attempt < FRONTEND_WAIT_ATTEMPTS; attempt++) {
      if (await deps.frontendUp()) {
        deps.openBrowser(url)
        return 'started'
      }
      await deps.sleep(FRONTEND_WAIT_MS)
    }
    return 'failed'
  }

  /** Tree-kills only the processes this supervisor started. */
  stopOwned(): void {
    for (const child of this.owned.values()) {
      if (child.pid !== undefined) this.deps.killTree(child.pid)
    }
    this.owned.clear()
  }

  private track(name: 'backend' | 'frontend', child: Child): void {
    this.owned.set(name, child)
    child.onExit(() => {
      if (this.owned.get(name) === child) this.owned.delete(name)
    })
  }
}
