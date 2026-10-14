import * as path from 'node:path'

export interface Config {
  repoRoot: string
  backendPort: number
  frontendPort: number
}

const portFrom = (value: string | undefined, fallback: number): number => {
  const port = Number(value)
  return Number.isInteger(port) && port > 0 && port < 65536 ? port : fallback
}

/** Ports come from the environment Start-Widget.ps1 resolves (args, .env, env, defaults). */
export function loadConfig(env: NodeJS.ProcessEnv = process.env): Config {
  return {
    // dist/main/config.js -> widget/dist/main -> repo root is three levels up.
    repoRoot: path.resolve(__dirname, '..', '..', '..'),
    backendPort: portFrom(env.BACKEND_PORT, 8501),
    frontendPort: portFrom(env.FRONTEND_PORT, 4173),
  }
}
