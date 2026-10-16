// The renderer is plain HTML/CSS plus tsc output; nothing bundles it, so copy the static files.
import { copyFileSync, mkdirSync } from 'node:fs'

mkdirSync('dist/ui/renderer', { recursive: true })
for (const file of ['index.html', 'style.css', 'tooltip.html', 'tooltip.css']) {
  copyFileSync(`src/renderer/${file}`, `dist/ui/renderer/${file}`)
}
