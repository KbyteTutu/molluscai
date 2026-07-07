import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const sourcePath = fileURLToPath(new URL('../TaxonDetailView.vue', import.meta.url))

describe('TaxonDetailView', () => {
  it('does not render external Wikipedia summaries as raw HTML', () => {
    const source = readFileSync(sourcePath, 'utf8')

    expect(source).not.toContain('v-html')
    expect(source).toContain('{{ inaturalist.wikipedia_summary }}')
  })
})
