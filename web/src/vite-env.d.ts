/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** The API's port, for a built app calling it cross-origin (see api/client.ts). Defaults to 8501. */
  readonly VITE_API_PORT?: string;
}
