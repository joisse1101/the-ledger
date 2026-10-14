import * as http from 'node:http'
import type { AddressInfo } from 'node:net'

export interface Stub {
  port: number
  requests: { method: string; url: string; headers: http.IncomingHttpHeaders }[]
  close(): Promise<void>
}

/** A loopback HTTP server whose handler the test controls. */
export async function startStub(
  handler: (req: http.IncomingMessage, res: http.ServerResponse) => void,
): Promise<Stub> {
  const requests: Stub['requests'] = []
  const server = http.createServer((req, res) => {
    requests.push({ method: req.method ?? '', url: req.url ?? '', headers: req.headers })
    handler(req, res)
  })
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve))
  return {
    port: (server.address() as AddressInfo).port,
    requests,
    close: () =>
      new Promise<void>((resolve) => {
        server.closeAllConnections()
        server.close(() => resolve())
      }),
  }
}

export const json = (res: http.ServerResponse, status: number, body: unknown) => {
  res.writeHead(status, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify(body))
}
