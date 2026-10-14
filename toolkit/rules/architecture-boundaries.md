---
paths:
  - "**/*.py"
  - "**/*.java"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.ps1"
  - "**/*.sh"
  - "**/*.bat"
---
# Architecture boundaries

Structure across frontend, backend and shared code. Applies to code in every project.

- A backend module never imports frontend code, and a frontend module never imports backend code.
  Share through a shared package or generated definitions.
- A data or domain layer never imports web-framework code (request/response types, routers,
  middleware). Frameworks depend on it, not the reverse.
- A contract that crosses a boundary (for example client types mirroring server JSON) lives in
  one shared or generated definition. When the contract changes, change both sides together.
- Enforce authorization on the server. Hiding a control in the UI is not security.
- Validate configuration files against a schema at startup and fail fast on a mismatch. Keep
  environment-specific values and secrets out of code and out of committed config.
