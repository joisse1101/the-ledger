---
version: 2026-10-14
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.css"
  - "**/*.html"
---
# TypeScript and React

Adds TypeScript and React mechanics to [core-principles](core-principles.md); it does not restate them.

## Types

- Never use `any`. Use `unknown` and narrow it, including the error in a `catch`.
- Model closed sets as string-literal unions or discriminated unions, and type every exported
  function's parameters and return value.
- Type data from the network at the boundary and validate it there (for example with a schema
  library) rather than casting with `as`.

## Errors and async

- Check `response.ok` after `fetch` and throw on failure; never assume success.
- Never leave a promise floating: `await` it, return it, or handle its rejection.
- Run independent awaits together with `Promise.all`; do not await in sequence what does not depend
  on the previous result.

## State and immutability

- Never mutate state, props or shared objects. Copy with spread (`{ ...user, name }`, `[...items, x]`).
- Compute a value from props or state during render; do not copy it into state and sync it by effect.
- When new state depends on old state, use the functional update (`setCount(c => c + 1)`).

## Components and hooks

- Use function components with typed props. Keep hooks at the top level, never in conditions or loops.
- Give every effect a correct dependency list and clean up what it starts (timers, listeners,
  subscriptions, requests).
- Never call the backend from a component directly. Go through the project's single API client
  wrapper so auth, base URL and error handling live in one place.

## Prefer

- Extract a custom hook when stateful logic repeats; name it `useX`.
- Early returns or `&&` for simple conditional rendering; avoid nested ternaries in JSX.
- Colors and spacing from design tokens (CSS variables), not literals.
- Component styles in a colocated CSS module.
- Define breakpoints in one place and reference them everywhere.
- Views take the same data at every screen size; adapt layout with CSS, not different data.
