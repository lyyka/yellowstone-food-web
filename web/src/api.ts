import type { CatalogPayload, Dossier, GraphPayload, LedgerSpecies, QueryResult, ScenarioResult } from './types'

export async function fetchCatalog(): Promise<CatalogPayload> {
  const res = await fetch('/api/species')
  if (!res.ok) throw new Error('Could not load the species guide')
  return res.json()
}

export async function fetchGraph(): Promise<GraphPayload> {
  const res = await fetch('/api/graph')
  if (!res.ok) throw new Error('Could not load food web')
  return res.json()
}

export async function fetchDossier(id: string): Promise<Dossier> {
  const res = await fetch(`/api/species/${id}`)
  if (!res.ok) throw new Error('Species not found in this web')
  return res.json()
}

export async function removeSpecies(id: string): Promise<QueryResult> {
  const res = await fetch('/api/remove', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function runScenario(text: string): Promise<ScenarioResult> {
  const res = await fetch('/api/scenario', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || 'Scenario failed')
  }
  return res.json()
}

export async function fetchLedger(): Promise<{ species: LedgerSpecies[]; count: number }> {
  const res = await fetch('/api/admin/species')
  if (!res.ok) throw new Error('Could not load the ledger')
  return res.json()
}

export async function createSpecies(body: Record<string, unknown>): Promise<LedgerSpecies> {
  const res = await fetch('/api/admin/species', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await readDetail(res))
  return res.json()
}

export async function updateSpecies(id: string, body: Record<string, unknown>): Promise<LedgerSpecies> {
  const res = await fetch(`/api/admin/species/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await readDetail(res))
  return res.json()
}

export async function deleteSpecies(id: string): Promise<void> {
  const res = await fetch(`/api/admin/species/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await readDetail(res))
}

export async function importSpeciesCsv(file: File): Promise<{
  created: number
  updated: number
  errors: string[]
  skipped_eats: string[]
}> {
  const data = new FormData()
  data.append('file', file)
  const res = await fetch('/api/admin/species/import', { method: 'POST', body: data })
  if (!res.ok) throw new Error(await readDetail(res))
  return res.json()
}

async function readDetail(res: Response): Promise<string> {
  const body = await res.json().catch(() => ({}))
  return body.detail || res.statusText
}
