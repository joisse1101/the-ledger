import { describe, expect, it } from 'vitest'
import { Supervisor, type Child, type Deps, type SpawnSpec } from '../src/main/supervisor'

function fake(overrides: Partial<Deps> = {}) {
  const log = {
    spawned: [] as SpawnSpec[],
    ran: [] as SpawnSpec[],
    killed: [] as number[],
    opened: [] as string[],
    exits: [] as (() => void)[],
  }
  let nextPid = 100
  const deps: Deps = {
    spawn(spec) {
      log.spawned.push(spec)
      const child: Child = { pid: nextPid++, onExit: (cb) => log.exits.push(cb) }
      return child
    },
    async run(spec) {
      log.ran.push(spec)
      return true
    },
    backendUp: async () => false,
    frontendUp: async () => false,
    webDistExists: () => true,
    killTree: (pid) => void log.killed.push(pid),
    openBrowser: (url) => void log.opened.push(url),
    sleep: async () => {},
    paths: { apiDir: 'C:/r/api', webDir: 'C:/r/web', python: 'py.exe' },
    backendPort: 8501,
    frontendPort: 4173,
    ...overrides,
  }
  return { deps, log }
}

describe('backend ownership', () => {
  it('spawns the backend when nothing answers and kills it on stop', async () => {
    const { deps, log } = fake()
    const sup = new Supervisor(deps)
    expect(await sup.ensureBackend()).toBe('started')
    expect(log.spawned[0]).toMatchObject({
      command: 'py.exe',
      args: ['server.py', '--port', '8501', '--frontend-port', '4173'],
      cwd: 'C:/r/api',
    })
    sup.stopOwned()
    expect(log.killed).toEqual([100])
  })

  it('never kills a backend that was already running', async () => {
    const { deps, log } = fake({ backendUp: async () => true })
    const sup = new Supervisor(deps)
    expect(await sup.ensureBackend()).toBe('already-running')
    sup.stopOwned()
    expect(log.spawned).toEqual([])
    expect(log.killed).toEqual([])
  })

  it('does not spawn a second backend while its own is still starting', async () => {
    const { deps, log } = fake()
    const sup = new Supervisor(deps)
    await sup.ensureBackend()
    expect(await sup.ensureBackend()).toBe('starting')
    expect(log.spawned).toHaveLength(1)
  })

  it('forgets a child that exited so it can be started again, and does not kill it', async () => {
    const { deps, log } = fake()
    const sup = new Supervisor(deps)
    await sup.ensureBackend()
    log.exits[0]()
    sup.stopOwned()
    expect(log.killed).toEqual([])
    expect(await sup.ensureBackend()).toBe('started')
  })
})

describe('openLedger', () => {
  it('opens a running frontend without starting another', async () => {
    const { deps, log } = fake({ frontendUp: async () => true })
    const sup = new Supervisor(deps)
    expect(await sup.openLedger()).toBe('already-running')
    expect(log.spawned).toEqual([])
    expect(log.opened).toEqual(['http://localhost:4173'])
  })

  it('starts vite preview with BACKEND_PORT and opens the browser once it answers', async () => {
    let calls = 0
    const { deps, log } = fake({ frontendUp: async () => ++calls > 2 })
    const sup = new Supervisor(deps)
    expect(await sup.openLedger()).toBe('started')
    expect(log.ran).toEqual([])
    expect(log.spawned[0]).toMatchObject({
      command: 'npm',
      args: ['run', 'preview', '--', '--port', '4173'],
      cwd: 'C:/r/web',
      env: { BACKEND_PORT: '8501' },
    })
    expect(log.opened).toEqual(['http://localhost:4173'])
    sup.stopOwned()
    expect(log.killed).toEqual([100])
  })

  it('builds first only when web/dist is missing', async () => {
    let calls = 0
    const { deps, log } = fake({ webDistExists: () => false, frontendUp: async () => ++calls > 1 })
    await new Supervisor(deps).openLedger()
    expect(log.ran.map((s) => s.args)).toEqual([['run', 'build']])
  })

  it('does not start the frontend when the build fails', async () => {
    const { deps, log } = fake({ webDistExists: () => false, run: async () => false })
    expect(await new Supervisor(deps).openLedger()).toBe('failed')
    expect(log.spawned).toEqual([])
    expect(log.opened).toEqual([])
  })

  it('never issues a gateway or docker command', async () => {
    let calls = 0
    const { deps, log } = fake({ webDistExists: () => false, frontendUp: async () => ++calls > 1 })
    const sup = new Supervisor(deps)
    await sup.ensureBackend()
    await sup.openLedger()
    const commands = [...log.spawned, ...log.ran].map((s) => `${s.command} ${s.args.join(' ')}`.toLowerCase())
    expect(commands.some((c) => /docker|gateway|nginx/.test(c))).toBe(false)
  })

  it('reuses its own frontend rather than starting a second while it is still coming up', async () => {
    const { deps, log } = fake()
    const sup = new Supervisor(deps)
    expect(await sup.openLedger()).toBe('failed')
    expect(await sup.openLedger()).toBe('failed')
    expect(log.spawned).toHaveLength(1)
  })
})
